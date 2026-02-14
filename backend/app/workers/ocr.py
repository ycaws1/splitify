import json
import uuid

import anthropic
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.receipt import Receipt, LineItem, ReceiptStatus


EXTRACTION_PROMPT = """Analyze this receipt/invoice image. Extract all information into this exact JSON structure:

{
  "merchant_name": "string",
  "receipt_date": "YYYY-MM-DD",
  "currency": "3-letter code e.g. MYR, USD",
  "line_items": [
    {
      "description": "item name",
      "quantity": 1.0,
      "unit_price": 0.00,
      "amount": 0.00
    }
  ],
  "subtotal": 0.00,
  "tax": 0.00,
  "service_charge": 0.00,
  "total": 0.00
}

Rules:
- Return ONLY valid JSON, no markdown or explanation.
- If a field is not visible, use null.
- amount = quantity * unit_price for each line item.
- Use the currency shown on the receipt, default to MYR if unclear.
"""


async def process_receipt_ocr(receipt_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
        receipt = result.scalar_one_or_none()
        if not receipt:
            return

        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "url", "url": receipt.image_url},
                            },
                            {"type": "text", "text": EXTRACTION_PROMPT},
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text
            data = json.loads(raw_text)

            receipt.merchant_name = data.get("merchant_name")
            receipt.receipt_date = data.get("receipt_date")
            receipt.currency = data.get("currency", "MYR")
            receipt.subtotal = data.get("subtotal")
            receipt.tax = data.get("tax")
            receipt.service_charge = data.get("service_charge")
            receipt.total = data.get("total")
            receipt.raw_llm_response = data
            receipt.status = ReceiptStatus.extracted

            for i, item in enumerate(data.get("line_items", [])):
                line_item = LineItem(
                    receipt_id=receipt.id,
                    description=item["description"],
                    quantity=item.get("quantity", 1),
                    unit_price=item["unit_price"],
                    amount=item["amount"],
                    sort_order=i,
                )
                db.add(line_item)

            await db.commit()

        except Exception:
            receipt.status = ReceiptStatus.processing  # stays in processing on failure
            await db.commit()

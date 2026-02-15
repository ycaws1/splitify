import json
import uuid
import logging
import base64

import google.generativeai as genai
import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.receipt import Receipt, LineItem, ReceiptStatus
from app.models.group import Group

logger = logging.getLogger(__name__)


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
- EXTRACT TAX explicitly. Look for keywords like "Tax", "GST", "SST", "VAT".
- EXTRACT SERVICE CHARGE explicitly. Look for keywords like "Service Charge", "SVC", "Svc Chg".
- Do not include tax or service charge in line items unless they are listed as line items. If they are summarily listed at the bottom, put them in tax/service_charge fields.
"""


async def fetch_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Fetch exchange rate from external API"""
    if from_currency == to_currency:
        return 1.0
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.exchangerate-api.com/v4/latest/{from_currency}",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                rate = data.get("rates", {}).get(to_currency)
                if rate:
                    logger.info(f"Fetched exchange rate: 1 {from_currency} = {rate} {to_currency}")
                    return float(rate)
    except Exception as e:
        logger.warning(f"Failed to fetch exchange rate: {e}")
    
    return 1.0  # Fallback


async def process_receipt_ocr(receipt_id: uuid.UUID, user_provided_currency: str | None = None) -> None:
    async with async_session_factory() as db:
        receipt = None
        try:
            # Fetch receipt
            result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
            receipt = result.scalar_one_or_none()
            
            if not receipt:
                logger.error(f"Receipt {receipt_id} not found")
                return

            # Download and encode image
            import time
            start_time = time.time()
            print(f"DEBUG: Downloading image from: {receipt.image_url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(receipt.image_url)
                response.raise_for_status()
                image_data = response.content
            
            download_time = time.time() - start_time
            print(f"DEBUG: Image downloaded in {download_time:.2f}s. Size: {len(image_data)} bytes")
                
            mime_type = "image/jpeg"
            if receipt.image_url.lower().endswith(".png"):
                mime_type = "image/png"
            elif receipt.image_url.lower().endswith(".webp"):
                mime_type = "image/webp"

            image_parts = [
                {
                    "mime_type": mime_type,
                    "data": image_data
                }
            ]

            # Configure Gemini
            genai.configure(api_key=settings.google_api_key)
            model_name = settings.google_model_name
            model = genai.GenerativeModel(model_name)
            
            ocr_start = time.time()
            print(f"DEBUG: Starting OCR with model {model_name}...")
            response = await model.generate_content_async([
                image_parts[0],
                EXTRACTION_PROMPT
            ])
            ocr_duration = time.time() - ocr_start
            
            raw_text = response.text
            
            print(f"DEBUG: Received OCR response for receipt {receipt_id} in {ocr_duration:.2f}s. Total time: {time.time() - start_time:.2f}s")
            
            # Remove markdown code blocks if present
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(raw_text)

            receipt.merchant_name = data.get("merchant_name")
            
            date_str = data.get("receipt_date")
            if date_str:
                try:
                    from datetime import datetime
                    # Try parsing simpler date formats too if complex one fails
                    try:
                        receipt.receipt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                         # Fallback for DD/MM/YYYY or similar if needed, or just let it fail
                        receipt.receipt_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    logger.warning(f"Invalid date format from OCR: {date_str}")
                    receipt.receipt_date = None
            else:
                receipt.receipt_date = None

            if user_provided_currency:
                receipt.currency = user_provided_currency
            else:
                receipt.currency = data.get("currency", "SGD")
            receipt.subtotal = data.get("subtotal")
            
            # Move Tax and Service Charge to line items for easier splitting
            # Always include them, even if 0
            def _get_val(v):
                if v is None: return 0.0
                try: return float(v)
                except: return 0.0

            tax_val = _get_val(data.get("tax"))
            svc_val = _get_val(data.get("service_charge"))
            
            receipt.tax = 0
            receipt.service_charge = 0
            
            # Append to line_items list
            if "line_items" not in data or data["line_items"] is None:
                data["line_items"] = []
                
            data["line_items"].append({
                "description": "Tax",
                "quantity": 1,
                "unit_price": tax_val,
                "amount": tax_val
            })
            data["line_items"].append({
                "description": "Service Charge",
                "quantity": 1,
                "unit_price": svc_val,
                "amount": svc_val
            })
            receipt.total = data.get("total")
            receipt.raw_llm_response = data
            
            # Fetch group's base currency
            group_result = await db.execute(select(Group).where(Group.id == receipt.group_id))
            group = group_result.scalar_one_or_none()
            base_currency = group.base_currency if group else "SGD"
            
            # Fetch exchange rate
            exchange_rate = await fetch_exchange_rate(receipt.currency, base_currency)
            receipt.exchange_rate = exchange_rate
            
            logger.info(f"Exchange rate for receipt {receipt_id}: 1 {receipt.currency} = {exchange_rate} {base_currency}")
            
            receipt.status = ReceiptStatus.extracted

            for i, item in enumerate(data.get("line_items", [])):
                line_item = LineItem(
                    receipt_id=receipt.id,
                    description=item.get("description", "Unknown Item"),
                    quantity=_get_val(item.get("quantity", 1)),
                    unit_price=_get_val(item.get("unit_price")),
                    amount=_get_val(item.get("amount")),
                    sort_order=i,
                )
                db.add(line_item)

            await db.commit()
            logger.info(f"Successfully processed receipt {receipt_id}")

        except Exception as e:
            import traceback
            print(f"DEBUG: OCR processing CRITICAL FAILURE for receipt {receipt_id}")
            traceback.print_exc()
            try:
                # Rollback the failed transaction so we can use the session again
                await db.rollback()
                
                if receipt:
                    # Refetch receipt to ensure it's attached to the new transaction state
                    # (Wait, receipt object is still valid but detached or state is confusing? 
                    # Actually, better to just update it. But strictly, we should maybe re-query if needed.
                    # However, since we just rolled back logic that modified it (but failed), 
                    # we can just set the status fields and commit.)
                    
                    # NOTE: We need to make sure we don't re-add invalid line items.
                    # Since we rolled back, line items are gone from DB. 
                    # Receipt modifications (merchant_name etc) are also gone from DB.
                    # So we update status on the CLEAN receipt row.
                    
                    receipt.status = ReceiptStatus.failed
                    receipt.raw_llm_response = {
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "stage": "processing"
                    }
                    # We might need to merge/add receipt back if it was detached? 
                    # But it was fetched in this session. Rollback invalidates it?
                    # SQLAlchemy async session: objects expire on commit/rollback.
                    # So accessing receipt.* triggers refresh.
                    
                    await db.commit()
            except Exception as commit_err:
                print(f"DEBUG: Failed to save error state for receipt {receipt_id}: {commit_err}")


import os
import sys
import json
import time # Import time for measuring duration
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    sys.exit(1)

# Use the same model as the app
MODEL_NAME = 'gemini-2.5-flash'

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

def process_image(image_path):
    print(f"Processing image: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return

    # Read image
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Determine mime type
    mime_type = "image/jpeg"
    if image_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        mime_type = "image/webp"
    
    # Configure Gemini
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    
    print(f"Sending request to {MODEL_NAME}...")
    start_time = time.time() # Start timer
    
    try:
        response = model.generate_content([
            {
                "mime_type": mime_type,
                "data": image_data
            },
            EXTRACTION_PROMPT
        ])
        
        end_time = time.time() # End timer
        duration = end_time - start_time
        
        print(f"\n--- Response Received in {duration:.2f} seconds ---") 
        print(response.text)
        print("\n--- Parsed JSON ---")
        
        # Clean markdown if present
        raw_text = response.text
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        try:
            data = json.loads(raw_text)
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_llm.py <path_to_image>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    process_image(image_path)

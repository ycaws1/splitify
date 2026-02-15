"""
List all available Gemini models
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure with your API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Available Gemini Models:")
print("=" * 80)

models = genai.list_models()

for model in models:
    print(f"\nModel: {model.name}")
    print(f"  Display Name: {model.display_name}")
    print(f"  Description: {model.description}")
    print(f"  Supported Generation Methods: {model.supported_generation_methods}")
    print(f"  Input Token Limit: {model.input_token_limit}")
    print(f"  Output Token Limit: {model.output_token_limit}")
    print("-" * 80)

print("\n\nModels that support 'generateContent' (for our OCR use case):")
print("=" * 80)

for model in models:
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")

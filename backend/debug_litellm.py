import asyncio
import os
from litellm import acompletion
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

async def test():
    try:
        res = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
            api_key=api_key
        )
        print("Success:", res.choices[0].message.content)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())

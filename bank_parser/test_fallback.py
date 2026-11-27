import sys
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="/Users/cmi_10139/Desktop/sasi/expense-analyzer/backend/.env")

API_KEYS = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY")
}

# Try Groq
if API_KEYS.get("GROQ_API_KEY"):
    try:
        from groq import Groq
        client = Groq(api_key=API_KEYS["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama-3.3-70b-versatile",
            temperature=0
        )
        print("Groq success!")
    except Exception as e:
        print("Groq AI parsing failed:", repr(e))


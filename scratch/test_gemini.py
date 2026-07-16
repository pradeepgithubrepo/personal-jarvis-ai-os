import os
from dotenv import load_dotenv
import httpx

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print("API Key:", api_key[:10] + "..." if api_key else "None")

url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.5-flash:generateContent?key={api_key}"
headers = {"Content-Type": "application/json"}
payload = {
    "contents": [
        {
            "parts": [
                {"text": "Hello, respond with 'Yes, I am working' if you see this."}
            ]
        }
    ]
}

try:
    r = httpx.post(url, json=payload, timeout=10.0)
    print("Status Code:", r.status_code)
    print("Response:", r.text)
except Exception as e:
    print("Error:", e)

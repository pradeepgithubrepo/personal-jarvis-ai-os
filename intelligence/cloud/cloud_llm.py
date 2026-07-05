# intelligence/cloud/cloud_llm.py

import os
import httpx
from loguru import logger

class CloudLLM:

    def ask(
        self,
        prompt: str,
    ) -> str:
        logger.info("Calling remote Cloud LLM (Gemini API)...")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set.")
            return "Cloud reasoning unavailable"
            
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            if r.status_code != 200:
                logger.error(f"Gemini API returned error code {r.status_code}: {r.text}")
                return "Cloud reasoning unavailable"
            
            resp_json = r.json()
            candidates = resp_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
                    
            logger.error("No valid candidates or parts returned from Gemini API.")
            return "Cloud reasoning unavailable"
            
        except Exception as e:
            logger.error(f"Failed to communicate with Gemini API: {e}")
            return "Cloud reasoning unavailable"
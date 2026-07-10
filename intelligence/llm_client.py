import os
import requests
import httpx
from loguru import logger
from configs.settings import settings

class LLMClient:
    def __init__(self, provider: str = None, model: str = None):
        # Default provider is settings.model_provider ("local") or "local"
        self.provider = provider or settings.model_provider or "local"
        
        # Determine Ollama URL
        url = settings.ollama_url or "http://localhost:11434"
        if "localhost" in url:
            url = url.replace("localhost", "127.0.0.1")
        self.ollama_url = url
        
        # Default local model is settings.local_model ("qwen2.5:1.5b")
        self.local_model = model or settings.local_model or "qwen2.5:1.5b"
        
        # Default cloud model/API key
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key

    def ask(self, prompt: str, provider: str = None, model: str = None, options: dict = None) -> str:
        """
        Generic entry point to ask local or cloud LLM.
        """
        target_provider = provider or self.provider
        target_model = model or self.local_model
        
        if target_provider == "local":
            return self._ask_local(prompt, target_model, options)
        elif target_provider in ["cloud", "gemini"]:
            return self._ask_cloud(prompt, options)
        else:
            logger.warning(f"Unknown LLM provider '{target_provider}'. Defaulting to local.")
            return self._ask_local(prompt, target_model, options)

    def _ask_local(self, prompt: str, model: str, options: dict = None) -> str:
        opts = {
            "temperature": 0.0,
            "num_predict": 256
        }
        if options:
            opts.update(options)
            
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": opts
            }
            res = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30.0)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                raise Exception(f"Ollama returned HTTP status {res.status_code}")
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            raise

    def _ask_cloud(self, prompt: str, options: dict = None) -> str:
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing for cloud request.")
            
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={self.gemini_api_key}"
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
                raise Exception(f"Gemini API returned error {r.status_code}: {r.text}")
                
            resp_json = r.json()
            candidates = resp_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            raise Exception("No valid content returned from Gemini API")
        except Exception as e:
            logger.error(f"Cloud LLM call failed: {e}")
            raise

import os
import requests
import httpx
from loguru import logger
from configs.settings import settings

class LLMClient:
    def __init__(self, provider: str = None, model: str = None):
        # Default provider priority hierarchy will run if provider is None
        self.provider = provider
        
        # Determine Ollama URL
        url = settings.ollama_url or "http://localhost:11434"
        if "localhost" in url:
            url = url.replace("localhost", "127.0.0.1")
        self.ollama_url = url
        
        # Default local model
        self.local_model = model or settings.local_model or "qwen2.5:1.5b"
        
        # Default cloud keys
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
        self.cerebras_api_key = os.environ.get("CEREBRAS_API_KEY") or settings.cerebras_api_key
        self.groq_api_key = os.environ.get("GROQ_API_KEY") or getattr(settings, "groq_api_key", None)
        self.mistral_api_key = os.environ.get("MISTRAL_API_KEY") or getattr(settings, "mistral_api_key", None)

    def ask(self, prompt: str, provider: str = None, model: str = None, options: dict = None) -> str:
        """
        Generic entry point to ask local or cloud LLM.
        If provider is None, runs the priority-based fallback hierarchy:
        Gemini -> Cerebras -> Local LLM.
        """
        target_provider = provider or self.provider
        
        # If a specific provider is explicitly requested, run only that provider
        if target_provider:
            if target_provider == "local":
                return self._ask_local(prompt, model or self.local_model, options)
            elif target_provider in ["cloud", "gemini"]:
                return self._ask_gemini(prompt, model or "gemini-2.5-flash", options)
            elif target_provider == "cerebras":
                return self._ask_cerebras(prompt, model or "gemma-4-31b", options)
            elif target_provider == "groq":
                return self._ask_groq(prompt, model or "llama-3.3-70b-versatile", options)
            elif target_provider == "mistral":
                return self._ask_mistral(prompt, model or "mistral-small-latest", options)
            else:
                logger.warning(f"Unknown LLM provider '{target_provider}'. Falling back to hierarchy.")

        # Fallback hierarchy
        errors = []
        
        # 1. Google Gemini (Priority 1)
        if self.gemini_api_key and getattr(self, "provider", None) != "mistral":
            try:
                logger.info("Attempting primary LLM provider: Gemini (gemini-2.5-flash)")
                return self._ask_gemini(prompt, model or "gemini-2.5-flash", options)
            except Exception as e:
                if "429" in str(e) or "throttle" in str(e).lower() or "too many requests" in str(e).lower():
                    logger.warning("Gemini returned throttle in fallback loop. Switching primary provider to Mistral.")
                    self.provider = "mistral"
                logger.warning(f"Gemini failed: {e}")
                errors.append(f"Gemini: {e}")
        else:
            logger.warning("Gemini API key is not configured or throttled, skipping primary provider.")
            errors.append("Gemini: Key missing or throttled")

        # 2. Cerebras Cloud (Priority 2)
        if self.cerebras_api_key:
            try:
                logger.info("Attempting fallback LLM provider: Cerebras (gemma-4-31b)")
                return self._ask_cerebras(prompt, model or "gemma-4-31b", options)
            except Exception as e:
                logger.warning(f"Cerebras failed: {e}")
                errors.append(f"Cerebras: {e}")
        else:
            logger.warning("Cerebras API key is not configured, skipping fallback provider.")
            errors.append("Cerebras: Key missing")

        # 3. Mistral Cloud (Priority 3)
        if self.mistral_api_key:
            try:
                logger.info("Attempting fallback LLM provider: Mistral (mistral-small-latest)")
                return self._ask_mistral(prompt, model or "mistral-small-latest", options)
            except Exception as e:
                logger.warning(f"Mistral failed: {e}")
                errors.append(f"Mistral: {e}")
        else:
            logger.warning("Mistral API key is not configured, skipping Mistral fallback provider.")
            errors.append("Mistral: Key missing")

        # 4. Local Ollama (Priority 4 - Last Resort)
        try:
            logger.info(f"Attempting last-resort LLM provider: Local Ollama ({self.local_model})")
            return self._ask_local(prompt, self.local_model, options)
        except Exception as e:
            logger.error(f"Local Ollama failed: {e}")
            errors.append(f"Local Ollama: {e}")

        # If all tiers failed, raise aggregated exception
        raise Exception(f"All LLM providers failed in fallback hierarchy: {'; '.join(errors)}")

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
            res = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120.0)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                raise Exception(f"Ollama returned HTTP status {res.status_code}")
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            raise

    def _ask_gemini(self, prompt: str, model: str, options: dict = None) -> str:
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing for cloud request.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
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
            if r.status_code == 429:
                logger.warning("Gemini returned 429 (throttled). Switching primary provider to Mistral.")
                self.provider = "mistral"
                if self.mistral_api_key:
                    return self._ask_mistral(prompt, "mistral-small-latest", options)
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
            if "429" in str(e) or "throttle" in str(e).lower() or "too many requests" in str(e).lower():
                logger.warning("Gemini exception indicates throttle. Switching primary provider to Mistral.")
                self.provider = "mistral"
                if self.mistral_api_key:
                    return self._ask_mistral(prompt, "mistral-small-latest", options)
            logger.error(f"Cloud Gemini call failed: {e}")
            raise

    def _ask_cerebras(self, prompt: str, model: str, options: dict = None) -> str:
        if not self.cerebras_api_key:
            raise ValueError("CEREBRAS_API_KEY is missing for Cerebras request.")
            
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cerebras_api_key}",
            "Content-Type": "application/json"
        }
        
        opts = {
            "temperature": 0.0
        }
        if options:
            opts.update(options)
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **opts
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30.0)
            if r.status_code == 429 or "too_many_requests_error" in r.text or "too_many_tokens_error" in r.text:
                logger.warning("Cerebras returned 429/throttle. Falling back to Mistral.")
                if self.mistral_api_key:
                    return self._ask_mistral(prompt, "mistral-small-latest", options)
            if r.status_code != 200:
                raise Exception(f"Cerebras API returned error {r.status_code}: {r.text}")
                
            resp_data = r.json()
            return resp_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Cerebras call failed: {e}")
            raise

    def _ask_groq(self, prompt: str, model: str, options: dict = None) -> str:
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing for Groq request.")
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        opts = {
            "temperature": 0.0
        }
        if options:
            opts.update(options)
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **opts
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30.0)
            if r.status_code == 429:
                logger.warning("Groq returned 429 (throttled). Falling back to Mistral.")
                if self.mistral_api_key:
                    return self._ask_mistral(prompt, "mistral-small-latest", options)
            if r.status_code != 200:
                raise Exception(f"Groq API returned error {r.status_code}: {r.text}")
                
            resp_data = r.json()
            return resp_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            raise

    def _ask_mistral(self, prompt: str, model: str, options: dict = None) -> str:
        if not self.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is missing for Mistral request.")
            
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        
        opts = {
            "temperature": 0.0
        }
        if options:
            opts.update(options)
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **opts
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30.0)
            if r.status_code != 200:
                raise Exception(f"Mistral API returned error {r.status_code}: {r.text}")
                
            resp_data = r.json()
            return resp_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Mistral call failed: {e}")
            raise

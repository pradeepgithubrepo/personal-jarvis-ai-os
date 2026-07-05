import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from intelligence.local.local_llm import LocalLLM

llm = LocalLLM()
print(f"Ollama URL: {llm.client._client.base_url}")
print(f"Model configured: {llm.model}")
print(f"Health check status: {llm.health_check()}")

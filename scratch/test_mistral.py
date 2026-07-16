import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.llm_client import LLMClient

def main():
    load_dotenv()
    print("Initializing LLMClient...")
    client = LLMClient()
    
    print("Testing Mistral provider directly...")
    try:
        response = client.ask("Respond with ONLY the word 'SUCCESS' if you receive this prompt.", provider="mistral")
        print(f"Mistral Response: {response}")
        if "SUCCESS" in response:
            print("✅ Mistral connection test PASSED!")
        else:
            print("❌ Mistral connection test returned unexpected response.")
    except Exception as e:
        print(f"❌ Mistral connection test FAILED with error: {e}")

if __name__ == "__main__":
    main()

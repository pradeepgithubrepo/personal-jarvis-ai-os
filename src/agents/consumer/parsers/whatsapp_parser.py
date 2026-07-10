import json

def parse_whatsapp(data_bytes: bytes) -> dict:
    try:
        content = json.loads(data_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON content: {str(e)}")
        
    if not isinstance(content, dict):
        raise ValueError("Root element of WhatsApp export must be a JSON object.")
        
    if "chat_name" not in content:
        raise ValueError("Missing required key 'chat_name' in WhatsApp export.")
        
    if "messages" not in content or not isinstance(content["messages"], list):
        raise ValueError("Missing or invalid 'messages' array in WhatsApp export.")
        
    return content

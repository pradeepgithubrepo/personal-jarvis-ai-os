import os
import sys
import traceback
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
dotenv.load_dotenv(".env")

from services.system_initializer import initialize_system
from consumer.consumer_service import ConsumerService

def main():
    initialize_system()
    service = ConsumerService()
    files = service.supabase_client.list_files("incoming")
    if not files:
        print("No files found!")
        return
        
    target_file = files[0]
    print(f"Tracing processing of: {target_file}")
    try:
        service._process_file(target_file)
    except Exception as e:
        print("Caught exception at top level:")
        traceback.print_exc()

if __name__ == "__main__":
    main()

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

load_dotenv()
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
opts = ClientOptions(schema="jarvis_insights_schemav1")
client = create_client(url, key, options=opts)

bucket_name = "jarvis-signals"
root_folder = "incoming"

try:
    print(f"Listing files in {bucket_name}/{root_folder}...")
    files = client.storage.from_(bucket_name).list(root_folder)
    file_names = [f["name"] for f in files if f.get("name") != ".emptyFolderPlaceholder"]
    
    print(f"Found {len(file_names)} files in incoming.")
    
    success_count = 0
    skipped_count = 0
    fail_count = 0
    
    for name in file_names:
        # Ignore subfolders
        if name in ["whatsapp", "sms", "gpay", "statements", "failed", "archive", "daily_briefs"]:
            continue
            
        from_path = f"{root_folder}/{name}"
        
        # Statements PDF should go to statements archive, other files go to legacy archive
        if name.lower().endswith(".pdf"):
            to_path = f"archive/statements/{name}"
        else:
            to_path = f"archive/{name}"
            
        print(f"Moving {from_path} -> {to_path}...")
        try:
            client.storage.from_(bucket_name).move(from_path, to_path)
            print(f"Successfully archived: {name}")
            success_count += 1
        except Exception as e:
            err_msg = str(e)
            if "already exists" in err_msg.lower() or "409" in err_msg:
                print(f"File already exists in archive, removing from incoming: {name}")
                try:
                    client.storage.from_(bucket_name).remove([from_path])
                    skipped_count += 1
                except Exception as ex:
                    print(f"Failed to remove duplicate: {ex}")
                    fail_count += 1
            else:
                print(f"Failed to move {name}: {e}")
                fail_count += 1
                
    print(f"\nCompleted! Archived: {success_count}, Cleared Duplicates: {skipped_count}, Failed: {fail_count}")

except Exception as e:
    print(f"Error during execution: {e}")

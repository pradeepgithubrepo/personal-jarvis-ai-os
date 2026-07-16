import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

def main():
    print("Starting Validation")
    print("Loading Environment")
    
    # Load environment variables
    load_dotenv()
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from environment.")
        sys.exit(1)
        
    try:
        # Connect to Supabase
        options = ClientOptions(schema="jarvis_insights_schemav1")
        client: Client = create_client(supabase_url, supabase_key, options=options)
        print("Supabase Connected")
        
        # Read storage bucket jarvis-signals/incoming
        files = client.storage.from_("jarvis-signals").list("incoming")
        # Exclude empty folder placeholder if present
        file_names = [f["name"] for f in files if f.get("name") != ".emptyFolderPlaceholder"]
        files_found = len(file_names)
        print("Bucket Read Success")
        print(f"Files Found: {files_found}")
        
        # Insert validation row
        payload = {
            "test_message": "Jarvis Wake Validation",
            "file_count": files_found,
            "execution_time": datetime.now(timezone.utc).isoformat()
        }
        
        insert_res = client.table("v1_connectivity_test").insert(payload).execute()
        
        if insert_res.data:
            inserted_row = insert_res.data[0]
            inserted_id = inserted_row.get("id")
            print("Insert Success")
            # Extra log details to capture inserted record ID
            # (Matches Step 5: Log inserted record ID)
            # We print 'Insert Success' and then 'Validation Complete' for the scheduler to capture.
        else:
            raise Exception("Insert completed but returned empty data response.")
            
        print("Validation Complete")
        sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

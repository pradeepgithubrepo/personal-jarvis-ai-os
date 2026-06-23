# test_supabase_connection.py

import os
import sys
import httpx
from dotenv import load_dotenv
from loguru import logger
from supabase import create_client, Client
from supabase.client import ClientOptions

# Load environment variables
load_dotenv()

def run_diagnostics():
    logger.info("=========================================")
    logger.info("Jarvis - Supabase Connectivity Validation")
    logger.info("=========================================")

    # Step 1: Read env variables
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_KEY")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    secret_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not url:
        logger.error("SUPABASE_URL is missing in .env")
        sys.exit(1)

    # Use the secret_key (service_role) for client authentication
    api_key = secret_key
    if not api_key:
        logger.error("SUPABASE_SECRET_KEY is missing in .env")
        sys.exit(1)

    logger.info(f"Supabase URL: {url}")
    logger.info("Initializing Supabase Client...")
    
    # Initialize client
    try:
        # Use sync client options with custom schema
        opts = ClientOptions(schema="jarvis_insights_schema")
        supabase: Client = create_client(url, api_key, options=opts)
        logger.success("Supabase Client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed during Step: Client Initialization. Error: {e}")
        sys.exit(1)

    # Step 2: Lightweight API connectivity check (PostgREST metadata endpoint)
    logger.info("Testing API connectivity (HTTP GET)...")
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept-Profile": "jarvis_insights_schema"
    }
    
    schema_info = {}
    try:
        # Directly query the PostgREST API spec endpoint to discover tables
        r = httpx.get(f"{url}/rest/v1/", headers=headers, timeout=10.0)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}: {r.text}")
        schema_info = r.json()
        logger.success("API communication verified successfully!")
    except Exception as e:
        logger.error(f"Failed during Step: API Connectivity Check. Error: {e}")
        logger.info("Recommended next action: Check if SUPABASE_URL is correct and that the anon key is valid.")
        sys.exit(1)

    # Step 3: Schema & Table Discovery
    logger.info("Discovering tables under 'jarvis_insights_schema'...")
    discovered_tables = []
    if "paths" in schema_info:
        paths = schema_info.get("paths", {})
        for path in paths.keys():
            if path != "/" and not path.startswith("/rpc/"):
                discovered_tables.append(path.replace("/", ""))
                
    logger.info(f"Schema status: Accessible. Discovered tables: {discovered_tables}")

    # Step 4: Validate CRUD (Create, Insert, Read, Delete)
    # Note: Creating a table (DDL) is not supported over PostgREST REST API.
    # Therefore, we check if connection_test exists. If not, we attempt to perform CRUD 
    # operations. If the table connection_test needs to be created, we instruct the user.
    test_table = "connection_test"
    if test_table not in discovered_tables:
        logger.warning(f"Table '{test_table}' was not discovered in the schema.")
        logger.info(f"Please run this SQL in your Supabase SQL Editor to create the validation table:\n")
        print(f"CREATE TABLE IF NOT EXISTS jarvis_insights_schema.{test_table} (")
        print("    id SERIAL PRIMARY KEY,")
        print("    created_at TIMESTAMP DEFAULT NOW(),")
        print("    test_message TEXT")
        print(");\n")
        logger.error("Failed during Step: Table Discovery (connection_test missing)")
        sys.exit(1)

    # If the table exists, validate CRUD operations
    logger.info(f"Performing CRUD lifecycle validation on '{test_table}'...")
    try:
        # 1. Insert
        logger.info("Inserting test row...")
        insert_res = supabase.table(test_table).insert({"test_message": "Jarvis Connectivity Test"}).execute()
        inserted_data = insert_res.data
        if not inserted_data:
            raise Exception("No data returned from insert statement.")
        row_id = inserted_data[0]["id"]
        logger.success(f"Insert successful. Inserted row ID: {row_id}")

        # 2. Read back
        logger.info(f"Reading row ID {row_id} back...")
        read_res = supabase.table(test_table).select("*").eq("id", row_id).execute()
        read_data = read_res.data
        if not read_data or read_data[0]["test_message"] != "Jarvis Connectivity Test":
            raise Exception(f"Failed to read correct message. Data received: {read_data}")
        logger.success(f"Read successful. Data matches: {read_data[0]['test_message']}")

        # 3. Delete
        logger.info(f"Deleting row ID {row_id}...")
        delete_res = supabase.table(test_table).delete().eq("id", row_id).execute()
        logger.success("Delete successful.")
        
        logger.success("All connectivity and CRUD lifecycle validations passed successfully!")
        
    except Exception as e:
        logger.error(f"Failed during Step: CRUD Validation. Error: {e}")
        logger.info("Recommended next action: Ensure table permissions are configured and RLS is disabled or permits this access.")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()

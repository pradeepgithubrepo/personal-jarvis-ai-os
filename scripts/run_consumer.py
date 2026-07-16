import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Insert workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.consumer.orchestrator import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Jarvis V2 Consumer Agent Ingestion CLI")
    parser.add_argument(
        "--trigger",
        choices=["MANUAL", "SCHEDULED", "RETRY", "RECOVERY"],
        default="MANUAL",
        help="Pipeline trigger type (default: MANUAL)"
    )
    args = parser.parse_args()

    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not load_dotenv(dotenv_path):
        print(f"WARNING: Could not load .env from {dotenv_path}")

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variable missing.")
        sys.exit(1)

    try:
        # Initialize Supabase client targeting the baseline schema
        options = ClientOptions(schema="jarvis_insights_schemav1")
        client: Client = create_client(supabase_url, supabase_key, options=options)
        
        print(f"Starting consumer pipeline run with trigger: {args.trigger}")
        result = run_pipeline(client, args.trigger)
        
        print("\n--- Pipeline Run Execution Results ---")
        print(f"Status: {result.get('status')}")
        print(f"Files Found: {result.get('files_found')}")
        print(f"Files Processed: {result.get('files_processed')}")
        print(f"Files Skipped: {result.get('files_skipped')}")
        print(f"Files Failed: {result.get('files_failed')}")
        print(f"Signals Created: {result.get('signals_created')}")
        print(f"Duration: {result.get('duration_ms')} ms")
        
        if result.get("error_message"):
            print(f"Error Message: {result.get('error_message')}")
            sys.exit(1)
            
        if result.get("status") == "FAILED":
            sys.exit(1)
            
        sys.exit(0)

    except Exception as e:
        print(f"FATAL ERROR: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

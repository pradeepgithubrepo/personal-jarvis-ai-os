# scratch/list_bucket_files.py

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.system_initializer import initialize_system
from consumer.supabase_client import SupabaseClient

def list_all():
    initialize_system()
    client = SupabaseClient()
    
    folders = ["incoming", "archive", "pradeep", "shobana"]
    for folder in folders:
        files = client.list_files(folder)
        print(f"Folder: {folder} -> {files}")

if __name__ == "__main__":
    list_all()

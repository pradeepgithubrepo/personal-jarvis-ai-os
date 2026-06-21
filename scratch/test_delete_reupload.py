import httpx
import time

SUPABASE_URL = "https://tbwnyuampjoamgarwwoo.supabase.co"
BUCKET_NAME = "jarvis-signals"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRid255dWFtcGpvYW1nYXJ3d29vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5MzUwOTYsImV4cCI6MjA5NzUxMTA5Nn0.3CdCtROBH2l0wq8GVir9_3rWWZUtD9w2UWsz9caM3cg"

def run():
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {ANON_KEY}",
    }
    
    unique_id = int(time.time())
    filename = f"pradeep/test_delete_{unique_id}.json"
    content = '{"test": "delete behavior"}'
    
    # 1. Upload
    print(f"Uploading file '{filename}'...")
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
    res_upload = httpx.post(
        upload_url,
        headers={**headers, "Content-Type": "application/json"},
        content=content
    )
    print(f"Upload Status: {res_upload.status_code}")
    print(f"Upload Response: {res_upload.text}")
    
    if res_upload.status_code != 200:
        return

    # 2. Verify we can download it
    download_url = f"{SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET_NAME}/{filename}"
    res_download = httpx.get(download_url, headers=headers)
    print(f"\nDownload before delete Status: {res_download.status_code}")
    
    # 3. Delete
    print(f"\nDeleting file '{filename}'...")
    delete_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}"
    res_delete = httpx.request(
        "DELETE",
        delete_url,
        headers={**headers, "Content-Type": "application/json"},
        json={"prefixes": [filename]}
    )
    print(f"Delete Status: {res_delete.status_code}")
    print(f"Delete Response: {res_delete.text}")
    
    # 4. Verify download fails after delete
    res_download_after = httpx.get(download_url, headers=headers)
    print(f"\nDownload after delete Status: {res_download_after.status_code}")
    print(f"Download after delete Response: {res_download_after.text}")
    
    # 5. Try uploading again
    print(f"\nRe-uploading file '{filename}'...")
    res_reupload = httpx.post(
        upload_url,
        headers={**headers, "Content-Type": "application/json"},
        content=content
    )
    print(f"Re-upload Status: {res_reupload.status_code}")
    print(f"Re-upload Response: {res_reupload.text}")

if __name__ == "__main__":
    run()

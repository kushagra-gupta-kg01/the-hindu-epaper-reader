import json
import os

METADATA_FILE = "captured_logs/metadata.jsonl"

def main():
    if not os.path.exists(METADATA_FILE):
        print("Metadata file not found.")
        return
        
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
        
    print(f"Scanning {len(lines)} requests for Cookie/Authorization headers to epaper.thehindu.com...")
    
    headers_found = False
    for r in lines:
        url = r["url"]
        if "epaper.thehindu.com" not in url:
            continue
            
        req_headers = r.get("request_headers", {})
        # Case insensitive check for cookie, authorization
        auth_keys = [k for k in req_headers.keys() if k.lower() in ["cookie", "authorization", "x-auth-token"]]
        if auth_keys:
            print(f"\n[Found Auth Headers in Request ID: {r['id']}]")
            print(f"URL: {url}")
            for k in auth_keys:
                # Truncate value for display to avoid listing private credentials fully in logs
                val = req_headers[k]
                truncated_val = val[:50] + "..." if len(val) > 50 else val
                print(f"  {k}: {truncated_val}")
            headers_found = True
            
    if not headers_found:
        print("No Cookie or Authorization headers were captured for epaper.thehindu.com.")

if __name__ == "__main__":
    main()

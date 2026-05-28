import json
import os

METADATA_FILE = "captured_logs/metadata.jsonl"

def main():
    if not os.path.exists(METADATA_FILE):
        print("Metadata file not found.")
        return
        
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
                
    json_requests = []
    for r in lines:
        if r["body_saved"] and r["body_file"].endswith(".json"):
            json_requests.append(r)
            
    print(f"Found {len(json_requests)} saved JSON response bodies:")
    for r in json_requests:
        filepath = os.path.join("captured_logs", r["body_file"])
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as bf:
                data = json.load(bf)
            
            # Print info
            print(f"File: {r['body_file']}")
            print(f"URL: {r['url']}")
            print(f"Size: {os.path.getsize(filepath)} bytes")
            
            # Print a snippet of keys or structure
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                # Print sample values for some keys
                for k in list(data.keys())[:3]:
                    val = str(data[k])
                    print(f"  {k}: {val[:120]}...")
            elif isinstance(data, list):
                print(f"List length: {len(data)}")
                if data:
                    print(f"First item: {str(data[0])[:200]}...")
            else:
                print(f"Data type: {type(data)}, value snippet: {str(data)[:200]}")
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            
        print("-" * 80)

if __name__ == "__main__":
    main()

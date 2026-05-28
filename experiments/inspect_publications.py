import json
import os

METADATA_FILE = "captured_logs/metadata.jsonl"
CATALOG_FILE = "captured_logs/bodies/1779960044203_52.json"

def main():
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
            
        print("=== Publications in Catalog ===")
        pubs = catalog.get("publications", [])
        for pub in pubs:
            pub_id = pub.get("id")
            pub_title = pub.get("title")
            issues = pub.get("issues", {}).get("web", [])
            print(f"Publication ID: {pub_id} | Title: {pub_title}")
            for issue in issues[:2]:
                print(f"  Issue ID: {issue.get('id')} | Issue Date: {issue.get('issueDate')} | Page Count: {issue.get('pageCount')}")
                print(f"  EPUB URL: {issue.get('epub')}")
    else:
        print("Catalog file not found.")

    print("\n=== All Captured Issue-Related URLs ===")
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        for r in lines:
            url = r["url"]
            if "/issues/" in url or "cciobjects.json" in url:
                print(f"[{r['status']}] {url}")

if __name__ == "__main__":
    main()

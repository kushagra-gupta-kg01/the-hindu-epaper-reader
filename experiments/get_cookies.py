from playwright.sync_api import sync_playwright
import json

def main():
    with sync_playwright() as p:
        print("Launching headless Google Chrome with persistent context...")
        user_data_dir = "./chrome_profile"
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=True
            )
            cookies = context.cookies("https://epaper.thehindu.com")
            print(f"Successfully retrieved {len(cookies)} cookies:")
            for c in cookies:
                print(f"  {c['name']}: {c['value'][:20]}... (domain: {c['domain']}, path: {c['path']})")
                
            # Write to a JSON file
            with open("cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            print("Saved cookies to cookies.json")
            
            context.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

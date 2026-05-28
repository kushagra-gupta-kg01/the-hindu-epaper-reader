# /// script
# dependencies = [
#     "playwright",
# ]
# ///

import os
import json
import sys
import time
import hashlib
from datetime import datetime
from playwright.sync_api import sync_playwright

LOG_DIR = os.path.abspath("captured_logs")
BODIES_DIR = os.path.join(LOG_DIR, "bodies")
METADATA_FILE = os.path.join(LOG_DIR, "metadata.jsonl")

# Ensure directories exist
os.makedirs(BODIES_DIR, exist_ok=True)

print(f"Logging directory: {LOG_DIR}")
print(f"Bodies directory: {BODIES_DIR}")
print(f"Metadata file: {METADATA_FILE}")

def get_extension(content_type):
    if not content_type:
        return "bin"
    content_type = content_type.lower()
    if "json" in content_type:
        return "json"
    if "html" in content_type:
        return "html"
    if "pdf" in content_type:
        return "pdf"
    if "javascript" in content_type or "js" in content_type:
        return "js"
    if "xml" in content_type:
        return "xml"
    if "text" in content_type:
        return "txt"
    if "image/svg" in content_type:
        return "svg"
    if "image/png" in content_type:
        return "png"
    if "image/jpeg" in content_type or "image/jpg" in content_type:
        return "jpg"
    return "bin"

def should_capture_body(url, content_type):
    if not content_type:
        return False
    
    content_type = content_type.lower()
    url = url.lower()
    
    # We want text-based content and PDFs
    text_or_data = any(t in content_type for t in ["json", "html", "text", "xml", "javascript", "pdf"])
    if text_or_data:
        return True
        
    # For images/binaries, only capture if they are from thehindu or epaper domains
    is_newspaper_domain = "thehindu" in url or "epaper" in url or "thg" in url
    is_image = "image/" in content_type
    if is_newspaper_domain and is_image:
        return True
        
    return False

response_count = 0

def main():
    global response_count
    
    with sync_playwright() as p:
        print("Launching Google Chrome...")
        
        # We use a local user data directory to ensure cookies, session info are retained,
        # but separate from the user's primary daily profile.
        user_data_dir = os.path.abspath("chrome_profile")
        
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,
                args=["--start-maximized"],
                no_viewport=True,
                bypass_csp=True # Bypass Content Security Policy to make injection/intercept easier
            )
        except Exception as e:
            print(f"Error launching system Chrome: {e}")
            print("Trying generic Chromium launch...")
            # Fallback if system Chrome fails
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--start-maximized"],
                no_viewport=True,
                bypass_csp=True
            )
            
        page = context.new_page()
        
        # Define response handler
        def handle_response(response):
            global response_count
            url = response.url
            status = response.status
            method = response.request.method
            
            # Skip analytics and trackers to prevent spamming logs
            if any(tracker in url for tracker in ["google-analytics", "doubleclick", "googletagmanager", "facebook.net", "scorecardresearch", "hotjar"]):
                return
                
            headers = dict(response.headers)
            content_type = headers.get("content-type", "")
            
            response_id = f"{int(time.time() * 1000)}_{response_count}"
            response_count += 1
            
            body_saved = False
            body_file_rel = None
            
            if should_capture_body(url, content_type):
                try:
                    # Get response body
                    body_bytes = response.body()
                    ext = get_extension(content_type)
                    filename = f"{response_id}.{ext}"
                    filepath = os.path.join(BODIES_DIR, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(body_bytes)
                        
                    body_saved = True
                    body_file_rel = os.path.join("bodies", filename)
                except Exception as e:
                    # Some responses might not have a body (e.g. HTTP 204 or completed redirects)
                    pass
            
            # Record metadata
            meta = {
                "id": response_id,
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "url": url,
                "status": status,
                "content_type": content_type,
                "request_headers": dict(response.request.headers),
                "response_headers": headers,
                "body_saved": body_saved,
                "body_file": body_file_rel
            }
            
            try:
                with open(METADATA_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(meta) + "\n")
            except Exception as e:
                print(f"Error writing metadata: {e}")
                
        # Register the response listener
        page.on("response", handle_response)
        
        print("\n" + "="*60)
        print("Browser is ready! Opening The Hindu ePaper...")
        print("Please navigate to today's Delhi edition in the browser window.")
        print("All network activity is being logged in the background.")
        print("When you are done, close the browser window or press Ctrl+C in this terminal.")
        print("="*60 + "\n")
        
        try:
            page.goto("https://epaper.thehindu.com/")
        except Exception as e:
            print(f"Initial page load error (can ignore if you navigate manually): {e}")
            
        # Keep running until the browser window is closed or interrupted
        while True:
            try:
                if page.is_closed() or context.pages == []:
                    print("Browser window closed. Exiting capture.")
                    break
                time.sleep(1)
            except KeyboardInterrupt:
                print("\nInterrupted by user. Exiting capture.")
                break
            except Exception as e:
                # Page or context might have been closed
                break

if __name__ == "__main__":
    main()

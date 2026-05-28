# /// script
# dependencies = [
#     "beautifulsoup4",
#     "requests",
# ]
# ///

import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://epaper.thehindu.com/ccidist-ws/th/th_delhi/issues/186654/OPS/"
OUTPUT_DIR = "delhi_edition_2026_05_28"
PDF_DIR = os.path.join(OUTPUT_DIR, "pages")
ARTICLES_DIR = os.path.join(OUTPUT_DIR, "articles")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# Ensure output directories exist
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(ARTICLES_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Set up authenticated session
session = requests.Session()
cookies_loaded = False

if os.path.exists("cookies.json"):
    try:
        with open("cookies.json", "r") as f:
            cookies_list = json.load(f)
        for cookie in cookies_list:
            # requests expects domain and path parameters
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ".thehindu.com"),
                path=cookie.get("path", "/")
            )
        cookies_loaded = True
        print(f"Loaded {len(cookies_list)} cookies into session.")
    except Exception as e:
        print(f"Error loading cookies: {e}")
else:
    print("Warning: cookies.json not found. Requesting without cookies.")

# Set realistic browser User-Agent
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
})

def sanitize_filename(name):
    # Keep alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r'[^\w\s\-_]', '', name)
    sanitized = sanitized.strip().replace(' ', '_')
    return sanitized[:80] # Limit length

def download_file(url, local_path):
    # If the file already exists, check if it's the 10,734-byte redirect HTML.
    # If it is, delete it and download it again.
    if os.path.exists(local_path):
        if os.path.getsize(local_path) == 10734:
            try:
                os.remove(local_path)
            except:
                pass
        else:
            return True
            
    try:
        response = session.get(url, timeout=20)
        if response.status_code == 200:
            # Double check that we didn't get redirected to the registration page
            # (which would return the same HTML SPA page size, about 10.7 KB)
            if len(response.content) == 10734 or b"Epaper-The Hindu doesn't work properly" in response.content:
                print(f"Warning: Request for {url} returned the registration/landing page instead of the actual file.")
                return False
                
            with open(local_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"Failed to download {url}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def parse_article_html(html_content, article_id, image_mapping):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract Title/Headline
    headline = ""
    head_tag = soup.find(["h1", "h2", "h3"])
    if head_tag:
        headline = " ".join([p.get_text().strip() for p in head_tag.find_all("p")])
        if not headline:
            headline = head_tag.get_text().strip()
            
    # Extract Byline
    byline_name = ""
    byline_tag = soup.find("span", class_="byline_name")
    if byline_tag:
        byline_name = byline_tag.get_text().strip()
        
    # Extract Dateline
    dateline = ""
    dateline_tag = soup.find("span", class_="dateline")
    if dateline_tag:
        dateline = dateline_tag.get_text().strip()
        
    # Extract Body
    body_paragraphs = []
    body_tag = soup.find("div", class_="body")
    if body_tag:
        for p in body_tag.find_all("p"):
            p_text = p.get_text().strip()
            if p_text:
                body_paragraphs.append(p_text)
                
    # Extract Liftout / Pull Quote
    liftouts = []
    liftout_tag = soup.find("div", class_="liftout")
    if liftout_tag:
        for p in liftout_tag.find_all("p"):
            l_text = p.get_text().strip()
            if l_text:
                liftouts.append(l_text)
                
    # Construct Markdown
    md_content = []
    if headline:
        md_content.append(f"# {headline}\n")
    else:
        md_content.append(f"# Article {article_id}\n")
        
    meta = []
    if byline_name:
        meta.append(f"**Author:** {byline_name}")
    if dateline:
        meta.append(f"**Location:** {dateline}")
    if meta:
        md_content.append(" | ".join(meta) + "\n")
        
    md_content.append("---\n")
    
    # Embed images associated with this article
    if article_id in image_mapping:
        for img_filename in image_mapping[article_id]:
            # Use relative path from the article file to the images directory
            # Article is at articles/<page_dir>/<file>.md
            # Image is at images/<file>.jpg
            # So path is "../../images/{img_filename}"
            md_content.append(f"![Article Image](../../images/{img_filename})\n")
            
    # Body text
    for p in body_paragraphs:
        md_content.append(f"{p}\n")
        
    # Liftout quotes
    if liftouts:
        md_content.append("\n> **Key Highlights:**")
        for l in liftouts:
            md_content.append(f"> - *{l}*")
            
    return "\n".join(md_content)

def process_page(page, page_num):
    page_id = page.get("id")
    page_attrs = page.get("attributes", {})
    page_name = page_attrs.get("Name", f"Page_{page_num:02d}")
    page_rev = page_attrs.get("LastRev", "")
    
    clean_page_name = sanitize_filename(page_name)
    page_folder_name = f"page_{page_num:02d}_{clean_page_name}"
    page_pdf_name = f"{page_folder_name}.pdf"
    
    print(f"Processing Page {page_num:02d}: {page_name}...")
    
    # 1. Download PDF
    pdf_url = f"{BASE_URL}{page_id}+{page_id}_pdf.pdf"
    if page_rev:
        pdf_url += f"?rev={page_rev}"
    
    pdf_local_path = os.path.join(PDF_DIR, page_pdf_name)
    pdf_success = download_file(pdf_url, pdf_local_path)
    
    if pdf_success:
        print(f"  -> Downloaded PDF ({os.path.getsize(pdf_local_path)} bytes)")
    else:
        print(f"  -> Failed to download PDF for Page {page_num:02d}")
    
    # 2. Extract Articles
    sub_elements = page.get("children", [])
    articles = [s for s in sub_elements if s.get("kind") == "Article"]
    
    page_articles_dir = os.path.join(ARTICLES_DIR, page_folder_name)
    os.makedirs(page_articles_dir, exist_ok=True)
    
    page_articles_meta = []
    
    # Prepare image mapping
    image_mapping = {}
    for art in articles:
        art_id = art.get("id")
        art_contents = art.get("content", [])
        
        # Check for images in contents (Public/...)
        for c in art_contents:
            ref = c.get("reference", "")
            if "Public/" in ref and ref.endswith(".jpg"):
                img_url = f"{BASE_URL}{ref}"
                img_filename = sanitize_filename(os.path.basename(ref)) + ".jpg"
                img_local_path = os.path.join(IMAGES_DIR, img_filename)
                
                # Download image
                if download_file(img_url, img_local_path):
                    if art_id not in image_mapping:
                        image_mapping[art_id] = []
                    image_mapping[art_id].append(img_filename)
                    
        # Check for nested Photo elements
        for child in art.get("children", []):
            if child.get("kind") == "Photo":
                for c in child.get("content", []):
                    ref = c.get("reference", "")
                    if "Public/" in ref and ref.endswith(".jpg"):
                        img_url = f"{BASE_URL}{ref}"
                        img_filename = sanitize_filename(os.path.basename(ref)) + ".jpg"
                        img_local_path = os.path.join(IMAGES_DIR, img_filename)
                        
                        # Download image
                        if download_file(img_url, img_local_path):
                            if art_id not in image_mapping:
                                image_mapping[art_id] = []
                            image_mapping[art_id].append(img_filename)

    # Download and parse article HTMLs
    for idx, art in enumerate(articles):
        art_id = art.get("id")
        art_attrs = art.get("attributes", {})
        art_name = art_attrs.get("Name", f"Article_{idx:02d}")
        headline = art_attrs.get("Headline", "")
        
        # Get HTML reference
        art_contents = art.get("content", [])
        html_ref = None
        for c in art_contents:
            ref = c.get("reference", "")
            if ref.endswith(".html"):
                html_ref = ref
                break
                
        if not html_ref:
            # Try nested Text elements
            for child in art.get("children", []):
                if child.get("kind") == "Text":
                    for c in child.get("content", []):
                        ref = c.get("reference", "")
                        if ref.endswith(".html"):
                            html_ref = ref
                            break
                    if html_ref:
                        break
                        
        if html_ref:
            html_url = f"{BASE_URL}{html_ref}"
            try:
                resp = session.get(html_url, timeout=15)
                if resp.status_code == 200:
                    # Double check that we didn't get registration landing page
                    if len(resp.content) == 10734 or b"Epaper-The Hindu doesn't work properly" in resp.content:
                        continue
                        
                    md_text = parse_article_html(resp.text, art_id, image_mapping)
                    
                    # Determine filename
                    display_title = headline if headline else art_name
                    san_title = sanitize_filename(display_title)
                    if not san_title:
                        san_title = f"article_{art_id}"
                    md_filename = f"{idx:02d}_{san_title}.md"
                    md_local_path = os.path.join(page_articles_dir, md_filename)
                    
                    with open(md_local_path, "w", encoding="utf-8") as mf:
                        mf.write(md_text)
                        
                    page_articles_meta.append({
                        "id": art_id,
                        "headline": headline or art_name,
                        "filename": md_filename,
                        "relative_path": f"articles/{page_folder_name}/{md_filename}"
                    })
            except Exception as e:
                print(f"Error processing article {art_id}: {e}")
                
    return {
        "page_num": page_num,
        "page_name": page_name,
        "pdf_path": f"pages/{page_pdf_name}",
        "articles": page_articles_meta
    }

def main():
    print("Loading Delhi cciobjects.json...")
    with open("delhi_cciobjects.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pages = data.get("children", [])
    print(f"Found {len(pages)} pages to extract.")
    
    extracted_pages = []
    
    # Process pages using a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_page, page, i+1): i+1 for i, page in enumerate(pages)}
        
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                result = future.result()
                extracted_pages.append(result)
            except Exception as exc:
                print(f"Page {page_num} generated an exception: {exc}")
                
    # Sort pages by number
    extracted_pages.sort(key=lambda x: x["page_num"])
    
    # Generate README.md Index
    print("Generating README.md Index...")
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    
    readme = []
    readme.append("# The Hindu - Delhi Edition")
    readme.append(f"**Date:** 2026-05-28 | **Total Pages:** {len(extracted_pages)}\n")
    readme.append("Welcome to today's Delhi edition of *The Hindu*. Below is an interactive table of contents. Click on the page names to view their articles or click on **[PDF]** to view the full page layout.\n")
    readme.append("## Table of Contents\n")
    
    for ep in extracted_pages:
        page_num_str = f"{ep['page_num']:02d}"
        readme.append(f"### Page {page_num_str}: {ep['page_name']} ([PDF]({ep['pdf_path']}))")
        if ep["articles"]:
            for art in ep["articles"]:
                # Escape markdown bracket characters in headline
                clean_headline = art['headline'].replace('[', '\\[').replace(']', '\\]')
                readme.append(f"- [{clean_headline}]({art['relative_path']})")
        else:
            readme.append("- *No articles extracted for this page (contains ads or supplements)*")
        readme.append("") # Empty line
        
    with open(readme_path, "w", encoding="utf-8") as rf:
        rf.write("\n".join(readme))
        
    print(f"\nExtraction complete! Output is saved in the '{OUTPUT_DIR}' directory.")
    print(f"Open '{OUTPUT_DIR}/README.md' to navigate the newspaper.")

if __name__ == "__main__":
    main()

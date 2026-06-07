import json
import re
from bs4 import BeautifulSoup

NOISE_SUBSTRINGS = {
    "page1", "sirpage", "stadiump-age", "daily quiz", "science quiz", 
    "health quiz", "here is a quiz"
}

NOISE_EXACT = {
    "sudoku", "sudoku_solution", "scoreboard", "live telecast", "the results", "know your english",
    "feedback", "rgladpage", "askus", "big shot", "th_subscribe_qr_code_new", "th27 panel",
    "nearby_shape_new", "text_feedback", "the daily quiz", "the science quiz"
}

def _is_noise_article(headline: str) -> bool:
    if not headline:
        return True
    # Normalize all Unicode whitespace sequences (including \xa0) to single standard spaces
    h_clean = " ".join(headline.lower().split())
    if not h_clean:
        return True
    
    # 1. Underscores (internal/layout references)
    if "_" in h_clean:
        return True
        
    # 2. Promos and day-specific layout codes (e.g., "promo3 (2)", "th28 promo")
    if re.match(r"^promo(\s*(\d|_|\()|$)", h_clean):
        return True
    if re.match(r"^th\d+", h_clean):
        return True
    if h_clean.startswith("th27 promo") or h_clean.startswith("th27 nearby") or h_clean.startswith("news in numbers"):
        return True
        
    # 3. Layout references: word followed by number (e.g. "vertical1", "picture3", "v3", "p2")
    if re.match(r"^(vertical|picture|v|p)\d+$", h_clean):
        return True
        
    # 4. Pure numbers or alphanumeric page templates (e.g. "14805", "23bg", "27HyPointr")
    if re.match(r"^\d+$", h_clean):
        return True
    if re.match(r"^\d{2,}[a-zA-Z]{2,}", h_clean):
        return True
        
    # 5. Exact match layout words
    if h_clean in NOISE_EXACT:
        return True
        
    # 6. Specific layout substrings
    if any(s in h_clean for s in NOISE_SUBSTRINGS):
        return True
        
    return False


def parse_catalog(catalog_json: str, city_key: str) -> str:
    try:
        data = json.loads(catalog_json)
    except Exception as e:
        raise ValueError(f"Failed to parse catalog JSON: {e}")
        
    publications = data.get("publications", [])
    for pub in publications:
        if pub.get("id") == city_key:
            issues = pub.get("issues", {}).get("web", [])
            if issues:
                return str(issues[0].get("id"))
                
    raise ValueError(f"City key {city_key} not found")

def parse_cciobjects(cciobjects_json: str) -> dict:
    try:
        data = json.loads(cciobjects_json)
    except Exception as e:
        raise ValueError(f"Failed to parse cciobjects JSON: {e}")
        
    issue_id = data.get("id")
    pages_data = data.get("children", [])
    
    parsed_pages = []
    page_nodes = [p for p in pages_data if p.get("kind") == "Page"]
    
    for idx, page in enumerate(page_nodes):
        page_num = idx + 1
        attrs = page.get("attributes", {})
        page_name = attrs.get("Name", f"Page_{page_num:02d}")
        
        # Parse articles on this page
        page_children = page.get("children", [])
        parsed_articles = []
        
        for child in page_children:
            if child.get("kind") != "Article":
                continue
                
            art_id = child.get("id")
            art_attrs = child.get("attributes", {})
            art_name = art_attrs.get("Name", "")
            art_headline = art_attrs.get("Headline", "")
            
            # Find HTML reference
            html_ref = None
            for c in child.get("content", []):
                ref = c.get("reference", "")
                if ref.endswith(".html"):
                    html_ref = ref
                    break
                    
            if not html_ref:
                # Search nested Text elements
                for sub_child in child.get("children", []):
                    if sub_child.get("kind") == "Text":
                        for c in sub_child.get("content", []):
                            ref = c.get("reference", "")
                            if ref.endswith(".html"):
                                html_ref = ref
                                break
                        if html_ref:
                            break
                            
            # We only keep the article if it has an HTML content file associated with it and is not noise
            if html_ref and not _is_noise_article(art_headline or art_name):
                # Parse associated images from content list and nested Photo structures
                images = []
                for c in child.get("content", []):
                    ref = c.get("reference", "")
                    if "Public/" in ref and ref.endswith(".jpg"):
                        images.append(ref)
                
                for sub_child in child.get("children", []):
                    if sub_child.get("kind") == "Photo":
                        for c in sub_child.get("content", []):
                            ref = c.get("reference", "")
                            if "Public/" in ref and ref.endswith(".jpg"):
                                images.append(ref)
                seen_imgs = set()
                deduped_images = []
                for img in images:
                    img_lower = img.lower()
                    if img_lower not in seen_imgs:
                        seen_imgs.add(img_lower)
                        deduped_images.append(img)
                images = deduped_images
                parsed_articles.append({
                    "id": art_id,
                    "headline": art_headline or art_name,
                    "html_ref": html_ref,
                    "images": images
                })
                
        parsed_pages.append({
            "page_num": page_num,
            "page_name": page_name,
            "articles": parsed_articles
        })
        
    # Sort pages by page number
    parsed_pages.sort(key=lambda x: x["page_num"])
    
    return {
        "issue_id": issue_id,
        "pages": parsed_pages
    }

def parse_article(html_content: str, article_id: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Headline
    headline = ""
    head_tag = soup.find(["h1", "h2", "h3"])
    if head_tag:
        headline = " ".join([p.get_text().strip() for p in head_tag.find_all("p")])
        if not headline:
            headline = head_tag.get_text().strip()
            
    # Author / Byline
    byline_name = None
    byline_tag = soup.find("span", class_="byline_name")
    if byline_tag:
        byline_name = byline_tag.get_text().strip()
        
    # Dateline / Location
    dateline = None
    dateline_tag = soup.find("span", class_="dateline")
    if dateline_tag:
        dateline = dateline_tag.get_text().strip()
        
    # Body Paragraphs
    body_paragraphs = []
    body_tag = soup.find("div", class_="body")
    if body_tag:
        for p in body_tag.find_all("p"):
            p_text = p.get_text().strip()
            if p_text:
                body_paragraphs.append(p_text)
                
    # Highlights / Liftouts
    highlights = []
    liftout_tag = soup.find("div", class_="liftout")
    if liftout_tag:
        for p in liftout_tag.find_all("p"):
            l_text = p.get_text().strip()
            if l_text:
                highlights.append(l_text)
                
    return {
        "id": article_id,
        "headline": headline,
        "author": byline_name,
        "dateline": dateline,
        "body": body_paragraphs,
        "highlights": highlights
    }

import pytest
import re
from src.scraper import fetch_catalog, fetch_cciobjects, fetch_article_html
from src.parser import parse_catalog, parse_cciobjects, parse_article

@pytest.mark.e2e
def test_e2e_live_headlines():
    # Use today's date
    date = "2026-05-28"
    city = "th_delhi"
    
    # 1. Fetch catalog
    catalog_json = fetch_catalog(date, city)
    assert catalog_json is not None
    assert "publications" in catalog_json
    
    # 2. Parse catalog to get issue ID
    issue_id = parse_catalog(catalog_json, city)
    assert issue_id == "186654"
    
    # 3. Fetch cciobjects
    cciobjects_json = fetch_cciobjects(issue_id, city)
    assert cciobjects_json is not None
    
    # 4. Parse cciobjects
    parsed_data = parse_cciobjects(cciobjects_json)
    assert parsed_data["issue_id"] is not None
    assert len(parsed_data["pages"]) > 0
    
    # Check first page
    first_page = parsed_data["pages"][0]
    assert "page_num" in first_page
    assert "page_name" in first_page

@pytest.mark.e2e
def test_e2e_live_article():
    city = "th_delhi"
    issue_id = "186654"
    ref = "GKLG1M8CQ.1+GO1G1NQTF.1.html"
    
    # 1. Fetch HTML from server
    html_content = fetch_article_html(city, issue_id, ref)
    assert html_content is not None
    assert "<html" in html_content.lower()
    
    # 2. Parse article
    article = parse_article(html_content, "GO1G1NQTF.1")
    assert article["id"] == "GO1G1NQTF.1"
    assert "IIT team to conduct" in article["headline"]
    assert article["author"] == "Maitri Porecha"
    assert len(article["body"]) > 0

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


@pytest.mark.e2e
def test_e2e_top_headlines():
    import os
    from fastapi.testclient import TestClient
    from api.index import app
    from src import cache
    
    # 1. Skip if api key is missing
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("OPENROUTER_API_KEY not configured. Skipping live OpenRouter E2E test.")
        
    client = TestClient(app)
    date = "2026-05-28"
    city = "th_delhi"
    
    # Pre-clean cache to ensure we test full flow
    cache.clear(date, city)
    
    # 2. Trigger live fetch to /api/headlines
    resp_headlines = client.get(f"/api/headlines?date={date}&city={city}")
    assert resp_headlines.status_code == 200
    assert cache.exists(date, city)
    
    # 3. Trigger live top headlines generation
    resp_top = client.get(f"/api/top-headlines?date={date}&city={city}&generate=true&limit=3")
    assert resp_top.status_code == 200
    
    data = resp_top.json()
    assert data["status"] == "ready"
    assert len(data["top_articles"]) == 3
    
    for art in data["top_articles"]:
        assert "id" in art
        assert "headline" in art
        assert "html_ref" in art
        assert "images" in art
        assert "ratings" in art
        ratings = art["ratings"]
        assert "impact" in ratings
        assert "importance" in ratings
        assert "interest" in ratings
        assert "depth" in ratings
        assert "reason" in art
        assert isinstance(art["reason"], str)
        # Reason should be short/concise (max 15 words)
        words = art["reason"].split()
        assert len(words) <= 15
        
    # 4. Trigger subsequent call to verify served from cache
    resp_cache = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false&limit=2")
    assert resp_cache.status_code == 200
    data_cache = resp_cache.json()
    assert data_cache["status"] == "ready"
    assert len(data_cache["top_articles"]) == 2


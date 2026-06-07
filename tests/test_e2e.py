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
    import time
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
    
    try:
        # Pre-clean cache to ensure we test full flow
        cache.clear(date, city)
        
        # 2. Trigger live fetch to /api/headlines
        resp_headlines = client.get(f"/api/headlines?date={date}&city={city}")
        assert resp_headlines.status_code == 200
        assert resp_headlines.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        assert cache.exists(date, city)
        
        # 3. Trigger live top headlines generation (Cache Miss)
        resp_top = client.get(f"/api/top-headlines?date={date}&city={city}&generate=true&limit=3")
        assert resp_top.status_code == 200
        assert resp_top.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        
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
            
        # 4. Trigger subsequent call to verify served from cache (Cache Hit)
        start = time.time()
        resp_cache = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false&limit=2")
        elapsed_hit = time.time() - start
        
        assert resp_cache.status_code == 200
        assert elapsed_hit < 3.0
        assert resp_cache.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        
        data_cache = resp_cache.json()
        assert data_cache["status"] == "ready"
        assert len(data_cache["top_articles"]) == 2
    finally:
        cache.clear(date, city)


@pytest.mark.e2e
def test_e2e_top_headlines_direct_self_healing():
    import os
    from fastapi.testclient import TestClient
    from api.index import app
    from src import cache

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("OPENROUTER_API_KEY not configured. Skipping live OpenRouter E2E test.")

    client = TestClient(app)
    date = "2026-05-27"  # Separate date partition to isolate tests
    city = "th_delhi"

    try:
        cache.clear(date, city)

        # Call top-headlines directly (with generate=true) on a completely empty cache
        resp = client.get(f"/api/top-headlines?date={date}&city={city}&generate=true&limit=2")
        assert resp.status_code == 200
        assert resp.headers["Cache-Control"] == "public, max-age=31536000, immutable"

        data = resp.json()
        assert data["status"] == "ready"
        assert len(data["top_articles"]) == 2

        # Verify that the main layout headlines cache exists as a result of self-healing
        assert cache.exists(date, city) is True
    finally:
        cache.clear(date, city)


@pytest.mark.e2e
def test_e2e_validation_boundaries():
    from fastapi.testclient import TestClient
    from api.index import app
    from src import cache

    client = TestClient(app)
    city = "th_delhi"

    # 1. Invalid date format returns 422 with no-store
    resp_invalid_date = client.get(f"/api/top-headlines?date=invalid-date&city={city}")
    assert resp_invalid_date.status_code == 422
    assert "no-store" in resp_invalid_date.headers.get("Cache-Control", "")

    # 2. Invalid limit <= 0 returns 422 with no-store
    resp_invalid_limit = client.get(f"/api/top-headlines?date=2026-05-28&city={city}&limit=0")
    assert resp_invalid_limit.status_code == 422
    assert "no-store" in resp_invalid_limit.headers.get("Cache-Control", "")

    # 3. Cache Miss with generate=false returns not_generated with no-store
    date = "2026-05-28"
    try:
        cache.clear(date, city)
        resp_not_gen = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false")
        assert resp_not_gen.status_code == 200
        assert resp_not_gen.json() == {"status": "not_generated"}
        assert "no-store" in resp_not_gen.headers.get("Cache-Control", "")
    finally:
        cache.clear(date, city)


@pytest.mark.e2e
def test_e2e_top_headlines_limitless_caching():
    import os
    import time
    from fastapi.testclient import TestClient
    from api.index import app
    from src import cache

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("OPENROUTER_API_KEY not configured. Skipping live OpenRouter E2E test.")

    client = TestClient(app)
    date = "2026-05-28"
    city = "th_delhi"

    try:
        # Pre-clean cache
        cache.clear(date, city)

        # 1. First fetch with NO limit parameter (generates the full pool of articles)
        resp_full = client.get(f"/api/top-headlines?date={date}&city={city}&generate=true")
        assert resp_full.status_code == 200
        data_full = resp_full.json()
        assert data_full["status"] == "ready"

        full_len = len(data_full["top_articles"])
        assert full_len > 0

        # 2. Subsequent call with limit=10 (cache hit)
        start = time.time()
        resp_limit_10 = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false&limit=10")
        elapsed_10 = time.time() - start
        assert resp_limit_10.status_code == 200
        assert elapsed_10 < 3.0
        data_10 = resp_limit_10.json()
        assert data_10["status"] == "ready"
        assert len(data_10["top_articles"]) == min(10, full_len)

        # 3. Subsequent call with limit=20 (cache hit)
        start = time.time()
        resp_limit_20 = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false&limit=20")
        elapsed_20 = time.time() - start
        assert resp_limit_20.status_code == 200
        assert elapsed_20 < 3.0
        data_20 = resp_limit_20.json()
        assert data_20["status"] == "ready"
        assert len(data_20["top_articles"]) == min(20, full_len)

        # 4. Subsequent call with NO limit (cache hit, returns all)
        start = time.time()
        resp_limit_none = client.get(f"/api/top-headlines?date={date}&city={city}&generate=false")
        elapsed_none = time.time() - start
        assert resp_limit_none.status_code == 200
        assert elapsed_none < 3.0
        data_none = resp_limit_none.json()
        assert data_none["status"] == "ready"
        assert len(data_none["top_articles"]) == full_len

    finally:
        cache.clear(date, city)


@pytest.mark.e2e
def test_e2e_article_summary():
    import os
    from fastapi.testclient import TestClient
    from api.index import app
    from src import cache as src_cache

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("OPENROUTER_API_KEY not configured. Skipping live OpenRouter E2E test.")

    client = TestClient(app)
    date = "2026-05-28"
    city = "th_delhi"
    issue_id = "186654"
    ref = "GKLG1M8CQ.1+GO1G1NQTF.1.html"

    # Pre-clean summary cache
    article_id = "GO1G1NQTF.1"
    # Create summaries dir locally if needed
    local_path = src_cache.get_summary_filepath(date, city, article_id)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except:
            pass

    try:
        response = client.get(f"/api/article-summary?date={date}&city={city}&issue_id={issue_id}&ref={ref}&reason=test reason")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"

        data = response.json()
        assert "summary" in data
        assert len(data["summary"]) == 4
        for point in data["summary"]:
            assert isinstance(point, str)
            assert len(point.strip()) > 0
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass



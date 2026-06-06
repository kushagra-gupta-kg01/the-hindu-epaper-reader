import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import requests

# We import the app inside the tests to resolve during collection,
# but it will initially fail due to api/index.py not existing yet.
from api.index import app
from src import cache

client = TestClient(app)

def test_get_headlines_validation():
    # Test invalid date format raises 422
    response = client.get("/api/headlines?date=28-05-2026&city=th_delhi")
    assert response.status_code == 422
    
    # Test missing parameters raises 422
    response = client.get("/api/headlines?date=2026-05-28")
    assert response.status_code == 422

def test_get_headlines_cache_hit():
    # GIVEN the file is already cached on disk
    mock_headlines = {
        "date": "2026-05-28",
        "city": "th_delhi",
        "issue_id": "186654",
        "pages": [{"page_num": 1, "page_name": "Jacket_01", "articles": []}]
    }
    
    with patch("src.cache.exists", return_value=True) as mock_exists, \
         patch("src.cache.read", return_value=mock_headlines) as mock_read, \
         patch("src.scraper.fetch_catalog") as mock_fetch:
         
        # WHEN we call the endpoint
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        
        # THEN we get a successful cached response instantly
        assert response.status_code == 200
        assert response.json() == mock_headlines
        mock_exists.assert_called_once_with("2026-05-28", "th_delhi")
        mock_read.assert_called_once_with("2026-05-28", "th_delhi")
        mock_fetch.assert_not_called()

def test_get_headlines_cache_miss(catalog_mock_data, cciobjects_mock_data):
    # GIVEN the file is NOT cached on disk
    with patch("src.cache.exists", return_value=False) as mock_exists, \
         patch("src.scraper.fetch_catalog", return_value=catalog_mock_data) as mock_fetch_cat, \
         patch("src.scraper.fetch_cciobjects", return_value=cciobjects_mock_data) as mock_fetch_cci, \
         patch("src.cache.write", return_value=True) as mock_write:
         
        # WHEN we call the endpoint
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        
        # THEN we fetch the catalog & cciobjects, parse them, cache them, and return them
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-05-28"
        assert data["city"] == "th_delhi"
        # Verify issue_id is the numeric ID returned by catalog
        assert data["issue_id"] == "186654"
        assert len(data["pages"]) == 22
        
        mock_exists.assert_called_once_with("2026-05-28", "th_delhi")
        mock_fetch_cat.assert_called_once_with("2026-05-28", "th_delhi")
        mock_fetch_cci.assert_called_once_with("186654", "th_delhi")
        mock_write.assert_called_once()

def test_get_article_success(article_mock_html):
    # GIVEN the scraper returns mock HTML
    with patch("src.scraper.fetch_article_html", return_value=article_mock_html) as mock_fetch:
        # WHEN we request a single article
        response = client.get("/api/article?city=th_delhi&issue_id=186654&ref=GKLG1M8CQ.1+GO1G1NQTF.1.html")
        
        # THEN we return parsed article content
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "GO1G1NQTF.1"
        assert "IIT team to conduct" in data["headline"]
        assert data["author"] == "Maitri Porecha"
        assert len(data["body"]) > 0
        
        mock_fetch.assert_called_once_with("th_delhi", "186654", "GKLG1M8CQ.1+GO1G1NQTF.1.html")

def test_get_article_ssrf_mitigation():
    # GIVEN the endpoint does not accept direct URLs
    response = client.get("/api/article?url=http://169.254.169.254/latest/meta-data/")
    # Assert it fails with validation error (422) because required parameters are missing
    assert response.status_code == 422
    
def test_api_network_failure_502():
    # GIVEN the scraper fails due to network outage (cache miss)
    with patch("src.cache.exists", return_value=False), \
         patch("src.scraper.fetch_catalog", side_effect=requests.RequestException("Connection refused")):
         
        # WHEN we call the endpoint
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        
        # THEN the API returns HTTP 502 Bad Gateway with a clean error message
        assert response.status_code == 502
        assert "Unable to fetch newspaper data from server" in response.json()["detail"]

def test_static_index_serving():
    # GET request to root should serve index.html with HTML content type
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in response.text
    assert "<title>" in response.text

def test_static_css_serving():
    # GET request to /index.css should serve the stylesheet
    response = client.get("/index.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")

def test_static_js_serving():
    # GET request to /app.js should serve the app javascript logic
    response = client.get("/app.js")
    assert response.status_code == 200
    assert "application/javascript" in response.headers.get("content-type", "") or "text/javascript" in response.headers.get("content-type", "")

def test_headlines_payload_issue_id_matches_catalog(catalog_mock_data, cciobjects_mock_data):
    # GIVEN a cache miss where catalog resolves to "186654"
    with patch("src.cache.exists", return_value=False), \
         patch("src.scraper.fetch_catalog", return_value=catalog_mock_data), \
         patch("src.scraper.fetch_cciobjects", return_value=cciobjects_mock_data) as mock_fetch_cci, \
         patch("src.cache.write", return_value=True):
         
        # WHEN we fetch headlines
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        assert response.status_code == 200
        data = response.json()
        
        # THEN the issue_id must match the numeric ID used to query the cciobjects endpoint
        # (This protects against regressions where cciobjects_json ID 'GKLG1M8C9.1' overrides the URL ID)
        assert data["issue_id"] == "186654"
        mock_fetch_cci.assert_called_once_with("186654", "th_delhi")

def test_get_article_utf8_decoding():
    # GIVEN article HTML with special UTF-8 characters like smart quotes (e.g. \u2018 and \u2019)
    # In UTF-8, ‘threat’ is: \xe2\x80\x98threat\xe2\x80\x99
    utf8_html_bytes = b"""
    <!doctype html>
    <html>
     <body>
      <h1><p>TMC MLA held for \xe2\x80\x98threat\xe2\x80\x99 to BJP workers</p></h1>
      <div class="body">
       <p>Body text with \xe2\x80\x9cquotes\xe2\x80\x9d.</p>
      </div>
     </body>
    </html>
    """
    
    class MockRequestsResponse:
        def __init__(self):
            self.status_code = 200
            self.content = utf8_html_bytes
            self.encoding = 'ISO-8859-1'  # requests default for text/html
            self.headers = {}
        
        def raise_for_status(self):
            pass
        
        @property
        def text(self):
            return self.content.decode(self.encoding)
            
    mock_resp = MockRequestsResponse()
    
    with patch("requests.get", return_value=mock_resp):
        response = client.get("/api/article?city=th_delhi&issue_id=186654&ref=dummy.html")
        assert response.status_code == 200
        data = response.json()
        assert data["headline"] == "TMC MLA held for \u2018threat\u2019 to BJP workers"
        assert "\u201cquotes\u201d" in data["body"][0]
        assert "â" not in data["headline"]


def test_get_article_ref_no_html():
    with patch("src.scraper.fetch_article_html", return_value="<html><body><h1>Headline</h1></body></html>"):
        response = client.get("/api/article?city=th_delhi&issue_id=186654&ref=foo+bar")
        assert response.status_code == 200
        assert response.json()["id"] == "bar"


def test_get_headlines_value_error_400():
    with patch("src.service.get_headlines", side_effect=ValueError("Invalid city ID")):
        response = client.get("/api/headlines?date=2026-05-28&city=invalid_city")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid city ID"


def test_get_headlines_internal_error_500():
    with patch("src.service.get_headlines", side_effect=RuntimeError("Some database error")):
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        assert response.status_code == 500
        assert "Internal server error: Some database error" in response.json()["detail"]


def test_get_article_network_failure_502():
    with patch("src.scraper.fetch_article_html", side_effect=requests.RequestException("Connection failed")):
        response = client.get("/api/article?city=th_delhi&issue_id=186654&ref=foo+bar.html")
        assert response.status_code == 502
        assert "Unable to fetch article content from server: Connection failed" in response.json()["detail"]


def test_get_article_internal_error_500():
    with patch("src.scraper.fetch_article_html", side_effect=RuntimeError("File system error")):
        response = client.get("/api/article?city=th_delhi&issue_id=186654&ref=foo+bar.html")
        assert response.status_code == 500
        assert "Internal server error: File system error" in response.json()["detail"]


def test_top_headlines_validation():
    # 1. Invalid date format
    response = client.get("/api/top-headlines?date=28-05-2026&city=th_delhi")
    assert response.status_code == 422
    
    # 2. Invalid limit (negative)
    response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&limit=0")
    assert response.status_code == 422
    assert "limit must be a positive integer" in response.json()["detail"]


def test_top_headlines_cache_hit():
    mock_top_data = {
        "status": "ready",
        "top_articles": [
            {"id": "art_1", "headline": "Headline 1", "ratings": {"impact": 9}, "reason": "Reason 1"},
            {"id": "art_2", "headline": "Headline 2", "ratings": {"impact": 8}, "reason": "Reason 2"},
            {"id": "art_3", "headline": "Headline 3", "ratings": {"impact": 7}, "reason": "Reason 3"}
        ]
    }
    with patch("src.cache.read_top", return_value=mock_top_data) as mock_read:
         
        # When we fetch with limit=2
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        # Verify sliced list
        assert len(data["top_articles"]) == 2
        assert data["top_articles"][0]["id"] == "art_1"
        assert data["top_articles"][1]["id"] == "art_2"
        mock_read.assert_called_once_with("2026-05-28", "th_delhi")


def test_top_headlines_generate_false():
    with patch("src.cache.read_top", return_value={}) as mock_read:
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi")
        assert response.status_code == 200
        assert response.json() == {"status": "not_generated"}
        mock_read.assert_called_once_with("2026-05-28", "th_delhi")


def test_top_headlines_generate_zero_articles():
    # GIVEN main headlines has zero articles
    mock_headlines = {"pages": [{"articles": []}, {"articles": []}]}
    with patch("src.cache.read_top", return_value={}) as mock_read_top, \
         patch("src.cache.read", return_value=mock_headlines) as mock_read:
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 400
        assert "No articles available in this edition" in response.json()["detail"]
        mock_read_top.assert_called_once_with("2026-05-28", "th_delhi")
        mock_read.assert_called_once_with("2026-05-28", "th_delhi")


def test_top_headlines_generate_success():
    # GIVEN cache miss, main headlines present, and LLM is successful
    mock_headlines = {
        "pages": [
            {
                "page_num": 1,
                "page_name": "Front_Pg",
                "articles": [
                    {"id": "GO1G1NQTF.1", "headline": "Supreme Court Ruling", "html_ref": "ref1.html", "images": []},
                    {"id": "art_2", "headline": "Local News", "html_ref": "ref2.html", "images": ["img.jpg"]}
                ]
            }
        ]
    }
    mock_llm_result = [
        # Test case-insensitivity: LLM outputs lowercased ID and omits suffix
        {"id": "go1g1nqtf", "ratings": [9, 10, 8, 7], "reason": "SC election ruling."}
    ]

    with patch("src.cache.read_top", return_value={}) as mock_read_top, \
         patch("src.cache.read", return_value=mock_headlines) as mock_read, \
         patch("src.llm.rank_headlines", return_value=mock_llm_result) as mock_rank, \
         patch("src.cache.write_top", return_value=True) as mock_write:
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true&limit=1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        assert len(data["top_articles"]) == 1
        
        # Verify validation & enrichment: matches original ID with casing and suffix preserved
        article = data["top_articles"][0]
        assert article["id"] == "GO1G1NQTF.1"
        assert article["headline"] == "Supreme Court Ruling"
        assert article["html_ref"] == "ref1.html"
        assert article["ratings"] == {
            "impact": 9,
            "importance": 10,
            "interest": 8,
            "depth": 7
        }
        assert article["reason"] == "SC election ruling."
        
        # Verify it wrote the entire enriched top list (un-sliced) to cache
        mock_write.assert_called_once()
        args, kwargs = mock_write.call_args
        assert len(args[2]["top_articles"]) == 1


def test_top_headlines_generate_missing_api_key_500():
    mock_headlines = {"pages": [{"articles": [{"id": "a1", "headline": "Headline"}]}]}
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", side_effect=ValueError("OpenRouter API Key is not configured on the server.")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 500
        assert "OpenRouter API Key is not configured" in response.json()["detail"]


def test_top_headlines_generate_llm_error_502():
    mock_headlines = {"pages": [{"articles": [{"id": "a1", "headline": "Headline"}]}]}
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", side_effect=ValueError("OpenRouter API Error: Rate limit")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 502
        assert "AI Generation failed: OpenRouter API Error: Rate limit" in response.json()["detail"]


def test_top_headlines_generate_empty_selection_502():
    mock_headlines = {"pages": [{"articles": [{"id": "a1", "headline": "Headline"}]}]}
    # GIVEN the LLM returned empty list, or entirely hallucinated list (empty after validation)
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", return_value=[]):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 502
        assert "AI returned an empty selection list" in response.json()["detail"]


def test_top_headlines_self_healing_success():
    # GIVEN main headlines cache is missing
    mock_headlines = {
        "pages": [{"articles": [{"id": "art_1", "headline": "Headline"}]}],
        "issue_id": "186654",
        "date": "2026-05-28",
        "city": "th_delhi"
    }
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value={}), \
         patch("src.service.get_headlines", return_value=mock_headlines) as mock_get_h, \
         patch("src.llm.rank_headlines", return_value=[{"id": "art_1", "ratings": [1,2,3,4], "reason": "Reason"}]), \
         patch("src.cache.write_top", return_value=True):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 200
        mock_get_h.assert_called_once_with("2026-05-28", "th_delhi")


def test_top_headlines_self_healing_value_error_400():
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value={}), \
         patch("src.service.get_headlines", side_effect=ValueError("Invalid city ID")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=invalid_city&generate=true")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid city ID"


def test_top_headlines_self_healing_outage_502():
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value={}), \
         patch("src.service.get_headlines", side_effect=requests.RequestException("Connection refused")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 502
        assert "Unable to fetch newspaper data from server" in response.json()["detail"]


def test_normalize_id_empty():
    from api.index import normalize_id
    assert normalize_id(None) == ""
    assert normalize_id("") == ""


def test_top_headlines_self_healing_internal_error_500():
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value={}), \
         patch("src.service.get_headlines", side_effect=RuntimeError("DB error")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 500
        assert "Internal server error: DB error" in response.json()["detail"]


def test_top_headlines_llm_request_exception_502():
    mock_headlines = {"pages": [{"articles": [{"id": "a1", "headline": "Headline"}]}]}
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", side_effect=requests.RequestException("Timeout error")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 502
        assert "AI Generation failed: Timeout error" in response.json()["detail"]


def test_top_headlines_llm_generic_exception_502():
    mock_headlines = {"pages": [{"articles": [{"id": "a1", "headline": "Headline"}]}]}
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", side_effect=RuntimeError("Unexpected error")):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 502
        assert "AI Generation failed: Unexpected error" in response.json()["detail"]


def test_top_headlines_llm_missing_id_skipped():
    mock_headlines = {
        "pages": [
            {
                "page_num": 1,
                "articles": [{"id": "GO1G1NQTF.1", "headline": "Headline"}]
            }
        ]
    }
    mock_llm_result = [
        {"id": None, "ratings": [1, 2, 3, 4], "reason": "No ID"},
        {"id": "go1g1nqtf", "ratings": [9, 10, 8, 7], "reason": "Valid"}
    ]
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", return_value=mock_llm_result), \
         patch("src.cache.write_top", return_value=True):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_articles"]) == 1
        assert data["top_articles"][0]["id"] == "GO1G1NQTF.1"


def test_top_headlines_llm_invalid_ratings_fallback():
    mock_headlines = {
        "pages": [
            {
                "page_num": 1,
                "articles": [{"id": "GO1G1NQTF.1", "headline": "Headline"}]
            }
        ]
    }
    mock_llm_result = [
        {"id": "go1g1nqtf", "ratings": None, "reason": "No ratings"},
    ]
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", return_value=mock_llm_result), \
         patch("src.cache.write_top", return_value=True):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_articles"]) == 1
        assert data["top_articles"][0]["ratings"] == {
            "impact": 0,
            "importance": 0,
            "interest": 0,
            "depth": 0
        }


def test_headlines_cache_control_headers():
    from src.cache import get_ist_today_str
    today_str = get_ist_today_str()
    past_str = "2020-01-01"
    
    with patch("src.service.get_headlines", return_value={"pages": []}):
        # 1. Test today's date (hourly cache control)
        resp_today = client.get(f"/api/headlines?date={today_str}&city=th_delhi")
        assert resp_today.status_code == 200
        assert resp_today.headers["Cache-Control"] == "public, s-maxage=3600, stale-while-revalidate=86400"
        
        # 2. Test past date (immutable cache control)
        resp_past = client.get(f"/api/headlines?date={past_str}&city=th_delhi")
        assert resp_past.status_code == 200
        assert resp_past.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_top_headlines_llm_malformed_item_skipped():
    mock_headlines = {
        "pages": [
            {
                "page_num": 1,
                "articles": [{"id": "GO1G1NQTF.1", "headline": "Headline"}]
            }
        ]
    }
    # LLM returns a malformed non-dict string element along with a valid dict element
    mock_llm_result = [
        "malformed_string_item",
        {"id": "go1g1nqtf", "ratings": [9, 10, 8, 7], "reason": "Valid"}
    ]
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", return_value=mock_llm_result), \
         patch("src.cache.write_top", return_value=True):
         
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_articles"]) == 1
        assert data["top_articles"][0]["id"] == "GO1G1NQTF.1"


def test_top_headlines_write_failure_non_fatal():
    mock_headlines = {
        "pages": [
            {
                "page_num": 1,
                "articles": [{"id": "GO1G1NQTF.1", "headline": "Headline"}]
            }
        ]
    }
    mock_llm_result = [
        {"id": "go1g1nqtf", "ratings": [9, 10, 8, 7], "reason": "Valid"}
    ]
    with patch("src.cache.read_top", return_value={}), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.llm.rank_headlines", return_value=mock_llm_result), \
         patch("src.cache.write_top", return_value=False) as mock_write:
         
        # Make request
        response = client.get("/api/top-headlines?date=2026-05-28&city=th_delhi&generate=true")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert len(data["top_articles"]) == 1
        assert data["top_articles"][0]["id"] == "GO1G1NQTF.1"
        mock_write.assert_called_once()


def test_api_telemetry_middleware_success():
    mock_headlines = {"date": "2026-05-28", "city": "th_delhi", "pages": []}
    with patch("src.cache.exists", return_value=True), \
         patch("src.cache.read", return_value=mock_headlines), \
         patch("src.telemetry.log_event") as mock_log:
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        assert response.status_code == 200
        
        # Telemetry should be called once for cache read and once for request middleware processing
        assert mock_log.call_count >= 1
        events = [call[0][0] for call in mock_log.call_args_list]
        assert "request_processed" in events
        
        req_call = [call for call in mock_log.call_args_list if call[0][0] == "request_processed"][0]
        details = req_call[0][1]
        assert details["path"] == "/api/headlines"
        assert details["method"] == "GET"
        assert details["status_code"] == 200
        assert "duration_ms" in details

def test_api_telemetry_middleware_skipped_for_static():
    with patch("src.telemetry.log_event") as mock_log:
        response = client.get("/index.css")
        assert response.status_code == 200
        
        # Should not write telemetry for static files
        events = [call[0][0] for call in mock_log.call_args_list]
        assert "request_processed" not in events

def test_api_telemetry_middleware_unhandled_exception():
    with patch("src.service.get_headlines", side_effect=RuntimeError("Unexpected error")), \
         patch("src.cache.exists", return_value=False), \
         patch("src.telemetry.log_event") as mock_log:
        response = client.get("/api/headlines?date=2026-05-28&city=th_delhi")
        assert response.status_code == 500
        
        events = [call[0][0] for call in mock_log.call_args_list]
        assert "unhandled_exception" in events or "request_processed" in events


def test_api_unhandled_exception_logging_and_json_response():
    with patch("src.telemetry.log_event") as mock_log:
        response = client.get("/api/test-unhandled-error")
        assert response.status_code == 500
        
        # Verify it returns a structured JSON response
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Internal server error"
        
        # Verify the telemetry captured the unhandled exception
        events = [call[0][0] for call in mock_log.call_args_list]
        assert "unhandled_exception" in events
        
        # Check details of unhandled exception log
        err_call = [call for call in mock_log.call_args_list if call[0][0] == "unhandled_exception"][0]
        details = err_call[0][1]
        assert details["path"] == "/api/test-unhandled-error"
        assert details["method"] == "GET"
        assert "error" in details
        assert "traceback" in details
        assert "duration_ms" in details










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





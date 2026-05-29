import pytest
from unittest.mock import patch, MagicMock
import requests
from src.scraper import fetch_catalog, fetch_cciobjects, fetch_article_html, get_headers

def test_get_headers():
    headers = get_headers()
    assert "User-Agent" in headers
    assert "Accept" in headers

def test_fetch_catalog():
    mock_resp = MagicMock()
    mock_resp.text = "catalog text"
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = fetch_catalog("2026-05-28", "th_delhi")
        assert res == "catalog text"
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0].startswith("https://epaper.thehindu.com/ccidist-ws/th/")

def test_fetch_cciobjects():
    mock_resp = MagicMock()
    mock_resp.text = "cci text"
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = fetch_cciobjects("186654", "th_delhi")
        assert res == "cci text"
        mock_get.assert_called_once()
        assert "issues/186654" in mock_get.call_args[0][0]

def test_fetch_article_html():
    mock_resp = MagicMock()
    mock_resp.text = "article html"
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = fetch_article_html("th_delhi", "186654", "ref.html")
        assert res == "article html"
        mock_get.assert_called_once()
        assert "issues/186654/OPS/ref.html" in mock_get.call_args[0][0]

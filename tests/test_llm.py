import os
import json
import pytest
import requests
from unittest.mock import patch, MagicMock
from src.llm import rank_headlines


@pytest.fixture
def sample_headlines():
    return {
        "pages": [
            {
                "page_num": 1,
                "page_name": "Front_Pg",
                "articles": [
                    {"id": "art_1", "headline": "Major SC Decision <landmark>"},
                    {"id": "art_2", "headline": "Economy updates\nwith newlines"},
                ],
            },
            {
                "page_num": 2,
                "page_name": "Edit_01",
                "articles": [
                    {"id": "art_3", "headline": "The growth dilemma"},
                ],
            },
        ]
    }


def test_llm_missing_api_key(sample_headlines):
    # GIVEN OPENROUTER_API_KEY is not configured
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=True):
        # WHEN we call rank_headlines
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
        # THEN it raises ValueError
        assert "OpenRouter API Key is not configured" in str(excinfo.value)


def test_llm_success(sample_headlines):
    # GIVEN OpenRouter API is successful
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "ISO-8859-1"
    
    llm_payload = {
        "top_articles": [
            {
                "id": "art_1",
                "ratings": [9, 10, 8, 7],
                "reason": "SC election ruling."
            },
            {
                "id": "art_3",
                "ratings": [8, 9, 7, 8],
                "reason": "Analysis on economics."
            }
        ]
    }
    
    # Configure json() call
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```json\n" + json.dumps(llm_payload) + "\n```"
                }
            }
        ]
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response) as mock_post, \
         patch("src.telemetry.log_event") as mock_log:
         
        # WHEN we execute the ranking
        result = rank_headlines(sample_headlines, limit=2)
        
        # THEN it compiles the prompt correctly and returns parsed results
        assert result == llm_payload["top_articles"]
        mock_post.assert_called_once()
        
        # Verify call parameters
        args, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 50
        assert "openrouter/owl-alpha" in kwargs["json"]["model"]
        assert kwargs["json"]["models"][0] == "openrouter/owl-alpha"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        assert "mock_secret_key" in kwargs["headers"]["Authorization"]
        
        # Verify telemetry
        mock_log.assert_called_once()
        t_args, t_kwargs = mock_log.call_args
        assert t_args[0] == "llm_ranking"
        assert t_args[1]["article_count"] == 3
        assert "duration_ms" in t_args[1]
        assert t_args[1]["model"] == "openrouter/owl-alpha"



def test_llm_json_decode_error(sample_headlines):
    # GIVEN the LLM returns non-JSON text
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Here is the result: [invalid json"
                }
            }
        ]
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        # WHEN we parse the response
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        # THEN it raises Value error due to parsing failure
        assert "AI response was malformed" in str(excinfo.value)


def test_llm_rate_limit_error(sample_headlines):
    # GIVEN OpenRouter returns an error dictionary (rate limit / quota exceeded)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "error": {
            "message": "Resource rate limit exceeded",
            "code": 429
        }
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        # WHEN we execute
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        # THEN it extracts and throws the API error details
        assert "OpenRouter API Error: Resource rate limit exceeded" in str(excinfo.value)


def test_llm_http_error(sample_headlines):
    # GIVEN the HTTP request fails with a connection error
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", side_effect=requests.RequestException("Timeout/Outage")):
         
        # WHEN we execute
        with pytest.raises(requests.RequestException):
            rank_headlines(sample_headlines, limit=5)


def test_llm_json_parse_exception(sample_headlines):
    # GIVEN response.json() raises an exception
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Raw unparseable string"
    mock_response.json.side_effect = Exception("JSON parse error")

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        assert "AI response was malformed and could not be parsed as JSON: Raw unparseable string" in str(excinfo.value)


def test_llm_rate_limit_with_retry_after(sample_headlines):
    # GIVEN OpenRouter returns a 429 error payload with a Retry-After header
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "30"}
    mock_response.json.return_value = {
        "error": {
            "message": "Resource rate limit exceeded",
            "code": 429
        }
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        assert "OpenRouter API Error: Resource rate limit exceeded" in str(excinfo.value)


def test_llm_empty_choices(sample_headlines):
    # GIVEN OpenRouter returned 200 OK but choices is empty
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": []
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        assert "OpenRouter returned empty choices" in str(excinfo.value)


def test_llm_empty_message_content(sample_headlines):
    # GIVEN message content is missing or empty
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": ""
                }
            }
        ]
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
            
        assert "OpenRouter returned empty message content" in str(excinfo.value)


def test_llm_generic_markdown_codeblock(sample_headlines):
    # GIVEN response content starts with generic ``` instead of ```json
    mock_response = MagicMock()
    mock_response.status_code = 200
    llm_payload = {"top_articles": [{"id": "art_1", "ratings": [1, 2, 3, 4], "reason": "Reason"}]}
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```\n" + json.dumps(llm_payload) + "\n```"
                }
            }
        ]
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = rank_headlines(sample_headlines, limit=5)
        assert result == llm_payload["top_articles"]


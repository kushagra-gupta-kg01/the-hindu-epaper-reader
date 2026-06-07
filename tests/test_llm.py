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
        assert kwargs["timeout"] == 16
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


def test_llm_thread_local_session_proxy_coverage():
    from src.llm import ThreadLocalSessionProxy
    proxy = ThreadLocalSessionProxy()
    # Trigger instantiation
    assert isinstance(proxy.session, requests.Session)
    mock_session = MagicMock()
    proxy._local.session = mock_session
    
    proxy.get("http://test")
    mock_session.get.assert_called_once_with("http://test")
    
    proxy.post("http://test")
    mock_session.post.assert_called_once_with("http://test")
    
    proxy.put("http://test")
    mock_session.put.assert_called_once_with("http://test")
    
    proxy.delete("http://test")
    mock_session.delete.assert_called_once_with("http://test")
    
    proxy.head("http://test")
    mock_session.head.assert_called_once_with("http://test")


def test_llm_budget_truncation():
    # Construct a massive list of articles (e.g. 300 articles)
    large_articles = []
    for i in range(300):
        # Each line is approx 90 chars. 300 lines = 27,000 chars, which exceeds the 16,000 char limit.
        large_articles.append({"id": f"art_{i}", "headline": f"Massive headline number {i} with some long text to fill space"})
        
    massive_headlines = {
        "pages": [
            {
                "page_num": 1,
                "page_name": "Front_Pg",
                "articles": large_articles
            }
        ]
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"top_articles": []}'}}]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response) as mock_post:
         
        rank_headlines(massive_headlines, limit=5)
        
        # Verify that the post request was made
        assert mock_post.called
        args, kwargs = mock_post.call_args
        sent_prompt = kwargs["json"]["messages"][1]["content"]
        # Character length of sent prompt should be bounded and not include all 300 articles
        assert len(sent_prompt) < 20000
        # Check that the last article "art_299" is not in the prompt, indicating it was truncated
        assert "art_299" not in sent_prompt


def test_llm_status_not_200_json_no_error(sample_headlines):
    # GIVEN response status is 400, body is valid JSON but no 'error' key
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"message": "Bad request"}
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
        assert "HTTP 400" in str(excinfo.value)


def test_llm_status_not_200_non_json(sample_headlines):
    # GIVEN response status is 503, body is not JSON
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"
    mock_response.json.side_effect = Exception("JSON error")
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
        assert "AI response was malformed" in str(excinfo.value)


def test_llm_empty_models_fallback_fail(sample_headlines):
    # GIVEN MODELS_LIST is empty
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.MODELS_LIST", []):
         
        with pytest.raises(ValueError) as excinfo:
            rank_headlines(sample_headlines, limit=5)
        assert "All models in the OpenRouter fallback chain failed" in str(excinfo.value)


def test_summarize_article_success():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    
    llm_payload = {
        "summary": [
            "Bullet point one.",
            "Bullet point two.",
            "Bullet point three.",
            "Bullet point four."
        ]
    }
    
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(llm_payload)
                }
            }
        ]
    }

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response) as mock_post:
         
        result = summarize_article("Test Headline", "Test body paragraphs.", reason="editor reason")
        assert len(result) == 4
        assert result == llm_payload["summary"]
        assert mock_post.called
        
        # Verify it includes the reason in the prompt
        args, kwargs = mock_post.call_args
        sent_prompt = kwargs["json"]["messages"][1]["content"]
        assert "editor reason" in sent_prompt
        assert kwargs["timeout"] == 15


def test_summarize_article_missing_api_key():
    from src.llm import summarize_article
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=True):
        # Should fallback to local summary directly without erroring
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_timeout_fallback():
    from src.llm import summarize_article
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", side_effect=requests.RequestException("Timeout")):
         
        # Should fallback to local summary
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]
        assert "Refer to the main newspaper edition" in result[1]


def test_summarize_article_malformed_json_fallback():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Not a JSON content"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_invalid_length_padding():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    
    # Returns only 2 bullet points
    llm_payload = {
        "summary": [
            "Bullet point one.",
            "Bullet point two."
        ]
    }
    
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(llm_payload)
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert result[0] == "Bullet point one."
        assert result[1] == "Bullet point two."
        # Verify it padded to 4 elements
        assert result[2] == "Bullet point two."
        assert result[3] == "Bullet point two."


def test_summarize_article_timeout_fallback_with_reason():
    from src.llm import summarize_article
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", side_effect=requests.RequestException("Timeout")):
         
        result = summarize_article("Test Headline", "Test body.", reason="custom reason")
        assert len(result) == 4
        assert "Editor's Focus: custom reason." in result[2]


def test_summarize_article_empty_inputs():
    from src.llm import summarize_article
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", side_effect=requests.RequestException("Timeout")):
         
        result = summarize_article("", "", reason="")
        assert len(result) == 4
        assert "Key Event: ." in result[0]


def test_summarize_article_truncation():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    llm_payload = {"summary": ["B1", "B2", "B3", "B4"]}
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(llm_payload)}}]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response) as mock_post:
         
        result = summarize_article("Test Headline", "A" * 13000)
        assert len(result) == 4
        args, kwargs = mock_post.call_args
        sent_body = kwargs["json"]["messages"][1]["content"]
        assert "... [truncated]" in sent_body


def test_summarize_article_non_200_with_json_error():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {"error": {"message": "invalid model name"}}
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        # Should fallback to local summary
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_non_200_with_raw_text_error():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.encoding = "utf-8"
    mock_response.text = "Service Overloaded"
    mock_response.json.side_effect = Exception("Not JSON")
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_empty_choices():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {"choices": []}
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_empty_message_content():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_json_codeblock_wrapper():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```json\n{\n  \"summary\": [\"Point 1\", \"Point 2\", \"Point 3\", \"Point 4\"]\n}\n```"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert result == ["Point 1", "Point 2", "Point 3", "Point 4"]


def test_summarize_article_summary_field_not_list():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "{\"summary\": \"Not a list string\"}"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]


def test_summarize_article_empty_bullets_in_list():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "{\"summary\": [\"\", null, \"Valid Bullet\", \"  \", \"Another Bullet\"]}"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert result[0] == "Valid Bullet"
        assert result[1] == "Another Bullet"
        assert result[2] == "Another Bullet"
        assert result[3] == "Another Bullet"


def test_summarize_article_generic_codeblock_wrapper():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```\n{\n  \"summary\": [\"Point A\", \"Point B\", \"Point C\", \"Point D\"]\n}\n```"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert result == ["Point A", "Point B", "Point C", "Point D"]


def test_summarize_article_no_valid_bullets():
    from src.llm import summarize_article
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "{\"summary\": [\"\", null, \"  \"]}"
                }
            }
        ]
    }
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "mock_secret_key"}), \
         patch("src.llm.session.post", return_value=mock_response):
         
        result = summarize_article("Test Headline", "Test body.")
        assert len(result) == 4
        assert "Key Event: Test Headline." in result[0]






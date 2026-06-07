import os
import time
import datetime
import json
import requests
import pytest
from unittest.mock import patch, MagicMock
import src.cache
from src.cache import exists, read, write, clear, get_filepath, get_top_filepath, read_top, write_top, clear_top

# Helper to get current date in IST (UTC+5:30)
def get_ist_today_str():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    ist_now = utc_now.astimezone(ist_tz)
    return ist_now.strftime("%Y-%m-%d")

def test_cache_write_exists_and_read():
    date = "2026-05-28"
    city = "th_test_city"
    data = {"sample_key": "sample_value"}
    
    # Pre-clean
    clear(date, city)
    
    # 1. Assert doesn't exist
    assert not exists(date, city)
    
    # 2. Write data
    success = write(date, city, data)
    assert success
    
    # 3. Assert exists now
    assert exists(date, city)
    
    # 4. Read back and check contents
    cached_data = read(date, city)
    assert cached_data == data
    
    # Clean up
    clear(date, city)
    assert not exists(date, city)

def test_cache_ttl_past_date():
    # Past dates should never expire, even if the file is old
    past_date = "2020-01-01"
    city = "th_test_city"
    data = {"historical": "data"}
    
    clear(past_date, city)
    write(past_date, city, data)
    
    # Manually modify the file modification time to 5 days ago
    filepath = get_filepath(past_date, city)
    five_days_ago = time.time() - (5 * 24 * 3600)
    os.utime(filepath, (five_days_ago, five_days_ago))
    
    # Should still exist (past date)
    assert exists(past_date, city)
    
    clear(past_date, city)

def test_cache_ttl_today_date():
    # Today's date (in IST) should NOT expire even if the file is older than 24 hours (1 day)
    today_str = get_ist_today_str()
    city = "th_test_city"
    data = {"today": "data"}
    
    clear(today_str, city)
    
    # 1. Write today's cache (new file)
    write(today_str, city, data)
    assert exists(today_str, city)  # Should exist
    
    # 2. Set file time to 25 hours ago
    filepath = get_filepath(today_str, city)
    twenty_five_hours_ago = time.time() - (25 * 3600)
    os.utime(filepath, (twenty_five_hours_ago, twenty_five_hours_ago))
    
    # Should still report it exists (never expires)
    assert exists(today_str, city)
    
    clear(today_str, city)


def test_cache_write_failure_is_non_fatal():
    with patch("src.cache.os.makedirs", side_effect=OSError("read-only file system")):
        assert write("2026-05-27", "th_delhi", {"sample": "data"}) is False

def test_cache_directory_resolves_to_tmp_in_serverless():
    import importlib
    import src.cache
    
    # GIVEN the serverless environment variable is set
    with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "test_lambda_func"}):
        try:
            # Force recalculation of import-time global CACHE_DIR variable
            importlib.reload(src.cache)
            
            # THEN the filepath should point to /tmp
            path = src.cache.get_filepath("2026-05-27", "th_delhi")
            assert path.startswith("/tmp/thehindureader-cache")
            
            # Verify read/write in /tmp works successfully
            data = {"serverless": "data"}
            assert src.cache.write("2026-05-27", "th_delhi", data)
            assert src.cache.exists("2026-05-27", "th_delhi")
            assert src.cache.read("2026-05-27", "th_delhi") == data
        finally:
            # Ensure standard cache is restored for other tests
            src.cache.clear("2026-05-27", "th_delhi")
            importlib.reload(src.cache)


def test_cache_read_exception_returns_empty():
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=OSError("Read error")):
        assert read("2026-05-27", "th_delhi") == {}


def test_cache_write_replace_exception_removes_temp_file():
    with patch("os.makedirs"), \
         patch("builtins.open"), \
         patch("os.replace", side_effect=OSError("Replace error")), \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
        assert write("2026-05-27", "th_delhi", {"data": 1}) is False
        mock_remove.assert_called_once()


def test_cache_write_remove_exception_is_silenced():
    with patch("os.makedirs"), \
         patch("builtins.open"), \
         patch("os.replace", side_effect=OSError("Replace error")), \
         patch("os.path.exists", return_value=True), \
         patch("os.remove", side_effect=OSError("Remove error")):
        assert write("2026-05-27", "th_delhi", {"data": 1}) is False


def test_cache_clear_remove_exception_is_silenced():
    with patch("os.path.exists", return_value=True), \
         patch("os.remove", side_effect=OSError("Delete error")):
        # Should not raise any exception
        clear("2026-05-27", "th_delhi")


def test_top_cache_filepath():
    path = get_top_filepath("2026-05-28", "th_delhi")
    assert path.endswith("2026-05-28/th_delhi_top.json")


def test_top_cache_operations():
    date = "2026-05-28"
    city = "th_test_city"
    data = {"status": "ready", "top_articles": ["id1", "id2"]}
    
    # Pre-clean
    clear(date, city)
    clear_top(date, city)
    
    # 1. Assert doesn't exist by reading
    assert read_top(date, city) == {}
    
    # 2. Write main cache
    write(date, city, {"sample": "headlines"})
    
    # 3. Write top cache
    success = write_top(date, city, data)
    assert success
    
    # 4. Read back
    cached = read_top(date, city)
    assert cached == data
    
    # 5. Clear top cache
    clear_top(date, city)
    assert read_top(date, city) == {}
    
    # Cleanup
    clear(date, city)


def test_top_cache_ttl_and_dependency():
    today_str = get_ist_today_str()
    city = "th_test_city"
    main_data = {"sample": "headlines"}
    top_data = {"status": "ready", "top_articles": ["id1"]}
    
    clear(today_str, city)
    clear_top(today_str, city)
    
    # Write both fresh
    write(today_str, city, main_data)
    write_top(today_str, city, top_data)
    
    # 1. Test that they do NOT expire when they are 25 hours old
    main_path = get_filepath(today_str, city)
    top_path = get_top_filepath(today_str, city)
    twenty_five_hours_ago = time.time() - (25 * 3600)
    os.utime(main_path, (twenty_five_hours_ago, twenty_five_hours_ago))
    os.utime(top_path, (twenty_five_hours_ago, twenty_five_hours_ago))
    
    assert exists(today_str, city)
    assert read_top(today_str, city) == top_data
    
    # Cleanup
    clear(today_str, city)


def test_top_cache_clear_cohesion():
    date = "2026-05-28"
    city = "th_test_city"
    write(date, city, {"sample": "headlines"})
    write_top(date, city, {"status": "ready", "top_articles": []})
    
    assert exists(date, city)
    assert read_top(date, city) == {"status": "ready", "top_articles": []}
    
    # clear() should delete both files
    clear(date, city)
    assert not exists(date, city)
    assert read_top(date, city) == {}


def test_top_cache_read_exception():
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=OSError("Read error")):
        assert read_top("2026-05-27", "th_delhi") == {}


def test_top_cache_clear_top_exception_is_silenced():
    with patch("os.path.exists", return_value=True), \
         patch("os.remove", side_effect=OSError("Delete error")):
        # Should not raise exception
        clear_top("2026-05-27", "th_delhi")


def test_top_cache_write_replace_exception_removes_temp_file():
    with patch("os.makedirs"), \
         patch("builtins.open"), \
         patch("os.replace", side_effect=OSError("Replace error")), \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
        assert write_top("2026-05-27", "th_delhi", {"data": 1}) is False
        mock_remove.assert_called_once()


def test_top_cache_write_remove_exception_is_silenced():
    with patch("os.makedirs"), \
         patch("builtins.open"), \
         patch("os.replace", side_effect=OSError("Replace error")), \
         patch("os.path.exists", return_value=True), \
         patch("os.remove", side_effect=OSError("Remove error")):
        assert write_top("2026-05-27", "th_delhi", {"data": 1}) is False


def test_blob_cache_exists_hit():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "head") as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        assert exists("2026-05-28", "th_delhi") is True
        mock_head.assert_called_once_with("https://test.public.blob.vercel-storage.com/headlines/2026-05-28/th_delhi.json", timeout=3.0)


def test_blob_cache_exists_miss():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "head") as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        assert exists("2026-05-28", "th_delhi") is False


def test_blob_cache_exists_network_error():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "head", side_effect=requests.RequestException("Timeout")):
        assert exists("2026-05-28", "th_delhi") is False


def test_blob_cache_read_success():
    mock_data = {"key": "val"}
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_get.return_value = mock_response
        assert read("2026-05-28", "th_delhi") == mock_data
        mock_get.assert_called_once_with("https://test.public.blob.vercel-storage.com/headlines/2026-05-28/th_delhi.json", timeout=3.0)


def test_blob_cache_read_failure_or_network_error():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get", side_effect=requests.RequestException("Connection refused")):
        assert read("2026-05-28", "th_delhi") == {}


def test_blob_cache_write_success():
    mock_data = {"layout": "data"}
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "test_token_123"), \
         patch.object(src.cache.session, "put") as mock_put:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        assert write("2026-05-28", "th_delhi", mock_data) is True
        mock_put.assert_called_once_with(
            "https://blob.vercel-storage.com/headlines/2026-05-28/th_delhi.json",
            headers={
                "Authorization": "Bearer test_token_123",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "Content-Type": "application/json"
            },
            data=json.dumps(mock_data, indent=2),
            timeout=3.0
        )


def test_blob_cache_write_token_missing():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", None), \
         patch.object(src.cache.session, "put") as mock_put:
        assert write("2026-05-28", "th_delhi", {"data": 1}) is False
        mock_put.assert_not_called()


def test_blob_cache_write_network_failure():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "put", side_effect=requests.RequestException("Upload failed")):
        assert write("2026-05-28", "th_delhi", {"data": 1}) is False


def test_blob_cache_clear_success():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "delete") as mock_delete:
        clear("2026-05-28", "th_delhi")
        assert mock_delete.call_count == 2
        mock_delete.assert_any_call(
            "https://blob.vercel-storage.com/headlines/2026-05-28/th_delhi.json",
            headers={"Authorization": "Bearer token", "x-api-version": "1"},
            timeout=3.0
        )
        mock_delete.assert_any_call(
            "https://blob.vercel-storage.com/top-headlines/2026-05-28/th_delhi_top.json",
            headers={"Authorization": "Bearer token", "x-api-version": "1"},
            timeout=3.0
        )


def test_blob_read_top_success():
    mock_data = {"status": "ready", "top_articles": [{"id": "1"}]}
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_get.return_value = mock_response
        assert read_top("2026-05-28", "th_delhi") == mock_data
        mock_get.assert_called_once_with("https://test.public.blob.vercel-storage.com/top-headlines/2026-05-28/th_delhi_top.json", timeout=3.0)


def test_blob_read_top_failure_network_error():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get", side_effect=requests.RequestException("Timeout")):
        assert read_top("2026-05-28", "th_delhi") == {}


def test_blob_write_top_success():
    mock_data = {"status": "ready"}
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "put") as mock_put:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        assert write_top("2026-05-28", "th_delhi", mock_data) is True
        mock_put.assert_called_once_with(
            "https://blob.vercel-storage.com/top-headlines/2026-05-28/th_delhi_top.json",
            headers={
                "Authorization": "Bearer token",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "Content-Type": "application/json"
            },
            data=json.dumps(mock_data, indent=2),
            timeout=3.0
        )


def test_blob_write_top_token_missing():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", None), \
         patch.object(src.cache.session, "put") as mock_put:
        assert write_top("2026-05-28", "th_delhi", {"data": 1}) is False
        mock_put.assert_not_called()


def test_blob_write_top_network_failure():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "put", side_effect=requests.RequestException("Upload failed")):
        assert write_top("2026-05-28", "th_delhi", {"data": 1}) is False


def test_blob_clear_top_success():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "delete") as mock_delete:
        clear_top("2026-05-28", "th_delhi")
        mock_delete.assert_called_once_with(
            "https://blob.vercel-storage.com/top-headlines/2026-05-28/th_delhi_top.json",
            headers={"Authorization": "Bearer token", "x-api-version": "1"},
            timeout=3.0
        )


def test_blob_store_url_rstrip():
    import importlib
    with patch.dict(os.environ, {"VERCEL_BLOB_STORE_URL": "https://test.public.blob.vercel-storage.com/"}):
        importlib.reload(src.cache)
        assert src.cache.BLOB_STORE_URL == "https://test.public.blob.vercel-storage.com"
    # Restore clean state
    importlib.reload(src.cache)


def test_get_ist_today_str():
    from src.cache import get_ist_today_str
    today_str = get_ist_today_str()
    import re
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", today_str)


def test_blob_cache_read_status_not_200():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        assert read("2026-05-28", "th_delhi") == {}


def test_blob_cache_clear_token_missing():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", None), \
         patch.object(src.cache.session, "delete") as mock_delete:
        clear("2026-05-28", "th_delhi")
        mock_delete.assert_not_called()


def test_blob_cache_clear_network_error():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "delete", side_effect=requests.RequestException("Timeout")):
        # Should not raise exception
        clear("2026-05-28", "th_delhi")


def test_blob_read_top_status_not_200():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        assert read_top("2026-05-28", "th_delhi") == {}


def test_blob_clear_top_token_missing():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", None), \
         patch.object(src.cache.session, "delete") as mock_delete:
        clear_top("2026-05-28", "th_delhi")
        mock_delete.assert_not_called()


def test_blob_clear_top_network_error():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch("src.cache.BLOB_READ_WRITE_TOKEN", "token"), \
         patch.object(src.cache.session, "delete", side_effect=requests.RequestException("Timeout")):
         # Should not raise exception
         clear_top("2026-05-28", "th_delhi")


def test_blob_read_malformed_json_returns_empty():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Malformed JSON")
        mock_get.return_value = mock_resp
        assert read("2026-05-28", "th_delhi") == {}


def test_blob_read_top_malformed_json_returns_empty():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Malformed JSON")
        mock_get.return_value = mock_resp
        assert read_top("2026-05-28", "th_delhi") == {}


def test_cache_telemetry_read_hit():
    with patch("src.cache.BLOB_STORE_URL", ""), \
         patch("builtins.open", MagicMock()), \
         patch("json.load", return_value={"mock": "data"}), \
         patch("os.path.exists", return_value=True), \
         patch("src.telemetry.log_event") as mock_log:
        res = read("2026-05-28", "th_delhi")
        assert res == {"mock": "data"}
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "cache_read"
        assert args[1]["status"] == "hit"
        assert args[1]["location"] == "local"

def test_cache_telemetry_read_miss():
    with patch("src.cache.BLOB_STORE_URL", ""), \
         patch("os.path.exists", return_value=False), \
         patch("src.telemetry.log_event") as mock_log:
        res = read("2026-05-28", "th_delhi")
        assert res == {}
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "cache_read"
        assert args[1]["status"] == "miss"

def test_cache_telemetry_write_success():
    with patch("src.cache.BLOB_STORE_URL", ""), \
         patch("os.makedirs"), \
         patch("builtins.open"), \
         patch("json.dump"), \
         patch("os.replace"), \
         patch("src.telemetry.log_event") as mock_log:
        res = write("2026-05-28", "th_delhi", {"data": 1})
        assert res is True
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "cache_write"
        assert args[1]["status"] == "success"

def test_cache_telemetry_blob_timeout():
    with patch("src.cache.BLOB_STORE_URL", "https://test.public.blob.vercel-storage.com"), \
         patch.object(src.cache.session, "get", side_effect=requests.exceptions.ConnectTimeout("Connection timed out")), \
         patch("src.telemetry.log_event") as mock_log:
        res = read("2026-05-28", "th_delhi")
        assert res == {}
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == "cache_read"
        assert args[1]["status"] == "miss"
        assert args[1]["error"] == "ConnectTimeout"


def test_thread_local_session_proxy_coverage():
    from src.cache import ThreadLocalSessionProxy
    proxy = ThreadLocalSessionProxy()
    # Trigger instantiation
    assert isinstance(proxy.session, requests.Session)
    # Mock requests.Session instance returned by self.session
    mock_session = MagicMock()
    proxy._local.session = mock_session
    
    proxy.get("http://test", param="1")
    mock_session.get.assert_called_once_with("http://test", param="1")
    
    proxy.post("http://test", data="2")
    mock_session.post.assert_called_once_with("http://test", data="2")
    
    proxy.put("http://test", data="3")
    mock_session.put.assert_called_once_with("http://test", data="3")
    
    proxy.delete("http://test")
    mock_session.delete.assert_called_once_with("http://test")
    
    proxy.head("http://test")
    mock_session.head.assert_called_once_with("http://test")







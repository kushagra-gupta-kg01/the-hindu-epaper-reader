import os
import time
import datetime
import pytest
from unittest.mock import patch
from src.cache import exists, read, write, clear, get_filepath

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
    # Today's date (in IST) should expire if the file is older than 24 hours (1 day)
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
    
    # Should report it does not exist (expired)
    assert not exists(today_str, city)
    
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
    with patch("builtins.open", side_effect=OSError("Read error")):
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


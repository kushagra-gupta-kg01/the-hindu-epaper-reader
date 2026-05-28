import os
import time
import datetime
import pytest
from src.cache import exists, read, write, clear

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
    filepath = os.path.join("data", past_date, f"{city}.json")
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
    filepath = os.path.join("data", today_str, f"{city}.json")
    twenty_five_hours_ago = time.time() - (25 * 3600)
    os.utime(filepath, (twenty_five_hours_ago, twenty_five_hours_ago))
    
    # Should report it does not exist (expired)
    assert not exists(today_str, city)
    
    clear(today_str, city)

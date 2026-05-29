import os
import json
import time
import uuid
import datetime

is_serverless = (
    os.environ.get("VERCEL") is not None
    or os.environ.get("VERCEL_ENV") is not None
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    or os.environ.get("LAMBDA_TASK_ROOT") is not None
)
CACHE_DIR = os.environ.get("CACHE_DIR") or (
    "/tmp/thehindureader-cache" if is_serverless else "data"
)

def get_filepath(date: str, city: str) -> str:
    return os.path.join(CACHE_DIR, date, f"{city}.json")

def get_ist_today_str() -> str:
    # Strictly calculate current date in Indian Standard Time (UTC+5:30)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    ist_now = utc_now.astimezone(ist_tz)
    return ist_now.strftime("%Y-%m-%d")

def exists(date: str, city: str) -> bool:
    path = get_filepath(date, city)
    if not os.path.exists(path):
        return False
        
    # TTL Check: today's paper expires after 24 hours
    today_str = get_ist_today_str()
    if date == today_str:
        file_mtime = os.path.getmtime(path)
        # If older than 24 hours, count as expired (does not exist)
        if time.time() - file_mtime > 24 * 3600:
            return False
            
    return True

def read(date: str, city: str) -> dict:
    path = get_filepath(date, city)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write(date: str, city: str, data: dict) -> bool:
    path = get_filepath(date, city)
    directory = os.path.dirname(path)
    
    # Atomic write to prevent file corruption
    temp_path = f"{path}.tmp.{uuid.uuid4()}"
    try:
        os.makedirs(directory, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)
        return True
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def clear(date: str, city: str):
    path = get_filepath(date, city)
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass
    clear_top(date, city)

def get_top_filepath(date: str, city: str) -> str:
    return os.path.join(CACHE_DIR, date, f"{city}_top.json")

def top_exists(date: str, city: str) -> bool:
    if not exists(date, city):
        return False
    path = get_top_filepath(date, city)
    if not os.path.exists(path):
        return False
        
    data = read_top(date, city)
    if data.get("status") != "ready":
        return False
        
    today_str = get_ist_today_str()
    if date == today_str:
        file_mtime = os.path.getmtime(path)
        if time.time() - file_mtime > 24 * 3600:
            return False
            
    return True

def read_top(date: str, city: str) -> dict:
    path = get_top_filepath(date, city)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_top(date: str, city: str, data: dict) -> bool:
    path = get_top_filepath(date, city)
    directory = os.path.dirname(path)
    
    # Atomic write to prevent file corruption
    temp_path = f"{path}.tmp.{uuid.uuid4()}"
    try:
        os.makedirs(directory, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)
        return True
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def clear_top(date: str, city: str):
    path = get_top_filepath(date, city)
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass

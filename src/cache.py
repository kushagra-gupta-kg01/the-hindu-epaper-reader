import os
import json
import uuid
import datetime
import requests
import logging

logger = logging.getLogger(__name__)

# Initialize requests Session for connection pooling
session = requests.Session()

# Vercel Blob configuration
BLOB_STORE_URL = os.environ.get("VERCEL_BLOB_STORE_URL")
if BLOB_STORE_URL:
    BLOB_STORE_URL = BLOB_STORE_URL.rstrip("/")

BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")

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

def get_top_filepath(date: str, city: str) -> str:
    return os.path.join(CACHE_DIR, date, f"{city}_top.json")

def get_blob_url(date: str, city: str) -> str:
    return f"{BLOB_STORE_URL}/headlines/{date}/{city}.json"

def get_top_blob_url(date: str, city: str) -> str:
    return f"{BLOB_STORE_URL}/top-headlines/{date}/{city}_top.json"

def get_ist_today_str() -> str:
    # Calculate current date in Indian Standard Time (UTC+5:30)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    ist_now = utc_now.astimezone(ist_tz)
    return ist_now.strftime("%Y-%m-%d")

def exists(date: str, city: str) -> bool:
    if BLOB_STORE_URL:
        url = get_blob_url(date, city)
        try:
            resp = session.head(url, timeout=4.0)
            return resp.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"Error checking cache existence on Vercel Blob: {e}")
            return False

    # Fallback to local file cache
    path = get_filepath(date, city)
    return os.path.exists(path)

def read(date: str, city: str) -> dict:
    if BLOB_STORE_URL:
        url = get_blob_url(date, city)
        try:
            resp = session.get(url, timeout=4.0)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            logger.warning(f"Error reading cache from Vercel Blob: {e}")
            return {}

    # Fallback to local
    path = get_filepath(date, city)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write(date: str, city: str, data: dict) -> bool:
    if BLOB_STORE_URL:
        if not BLOB_READ_WRITE_TOKEN:
            logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot write to Vercel Blob.")
            return False
        
        # Write to Vercel Blob write endpoint
        url = f"https://blob.vercel-storage.com/headlines/{date}/{city}.json"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-api-version": "1",
            "x-add-random-suffix": "0",
            "Content-Type": "application/json"
        }
        try:
            resp = session.put(url, headers=headers, data=json.dumps(data, indent=2), timeout=4.0)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.warning(f"Error writing cache to Vercel Blob: {e}")
            return False

    # Fallback to local file cache
    path = get_filepath(date, city)
    directory = os.path.dirname(path)
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
    if BLOB_STORE_URL:
        if not BLOB_READ_WRITE_TOKEN:
            logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot clear Vercel Blob.")
            clear_top(date, city)
            return
        
        # Delete main cache
        url = f"https://blob.vercel-storage.com/headlines/{date}/{city}.json"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-api-version": "1"
        }
        try:
            session.delete(url, headers=headers, timeout=4.0)
        except requests.RequestException as e:
            logger.warning(f"Error deleting main cache from Vercel Blob: {e}")
        
        clear_top(date, city)
        return

    # Fallback to local file cache
    path = get_filepath(date, city)
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass
    clear_top(date, city)

def top_exists(date: str, city: str) -> bool:
    if not exists(date, city):
        return False

    if BLOB_STORE_URL:
        url = get_top_blob_url(date, city)
        try:
            resp = session.head(url, timeout=4.0)
            if resp.status_code != 200:
                return False
            data = read_top(date, city)
            return data.get("status") == "ready"
        except requests.RequestException as e:
            logger.warning(f"Error checking top cache existence on Vercel Blob: {e}")
            return False

    # Fallback to local file cache
    path = get_top_filepath(date, city)
    if not os.path.exists(path):
        return False
        
    data = read_top(date, city)
    if data.get("status") != "ready":
        return False
            
    return True

def read_top(date: str, city: str) -> dict:
    if BLOB_STORE_URL:
        url = get_top_blob_url(date, city)
        try:
            resp = session.get(url, timeout=4.0)
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            logger.warning(f"Error reading top cache from Vercel Blob: {e}")
            return {}

    # Fallback to local file cache
    path = get_top_filepath(date, city)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_top(date: str, city: str, data: dict) -> bool:
    if BLOB_STORE_URL:
        if not BLOB_READ_WRITE_TOKEN:
            logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot write to Vercel Blob.")
            return False
        
        # Write to Vercel Blob write endpoint
        url = f"https://blob.vercel-storage.com/top-headlines/{date}/{city}_top.json"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-api-version": "1",
            "x-add-random-suffix": "0",
            "Content-Type": "application/json"
        }
        try:
            resp = session.put(url, headers=headers, data=json.dumps(data, indent=2), timeout=4.0)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.warning(f"Error writing top cache to Vercel Blob: {e}")
            return False

    # Fallback to local file cache
    path = get_top_filepath(date, city)
    directory = os.path.dirname(path)
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
    if BLOB_STORE_URL:
        if not BLOB_READ_WRITE_TOKEN:
            logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot clear top Vercel Blob.")
            return
        
        # Delete top cache
        url = f"https://blob.vercel-storage.com/top-headlines/{date}/{city}_top.json"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-api-version": "1"
        }
        try:
            session.delete(url, headers=headers, timeout=4.0)
        except requests.RequestException as e:
            logger.warning(f"Error deleting top cache from Vercel Blob: {e}")
        return

    # Fallback to local file cache
    path = get_top_filepath(date, city)
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass

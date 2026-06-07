import os
import json
import uuid
import datetime
import requests
import logging

logger = logging.getLogger(__name__)

import threading

class ThreadLocalSessionProxy:
    def __init__(self):
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            self._local.session = requests.Session()
        return self._local.session

    def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

    def put(self, *args, **kwargs):
        return self.session.put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.session.delete(*args, **kwargs)

    def head(self, *args, **kwargs):
        return self.session.head(*args, **kwargs)

# Thread-safe session proxy configured at module level for connection pooling
session = ThreadLocalSessionProxy()

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
            resp = session.head(url, timeout=3.0)
            return resp.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"Error checking cache existence on Vercel Blob: {e}")
            return False

    # Fallback to local file cache
    path = get_filepath(date, city)
    return os.path.exists(path)

def read(date: str, city: str) -> dict:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "miss"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    result = {}
    
    try:
        if BLOB_STORE_URL:
            url = get_blob_url(date, city)
            try:
                resp = session.get(url, timeout=3.0)
                if resp.status_code == 200:
                    result = resp.json()
                    status = "hit"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error reading cache from Vercel Blob: {e}")
        else:
            path = get_filepath(date, city)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        result = json.load(f)
                        status = "hit"
                except Exception as e:
                    error_class = type(e).__name__
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_read", details)
        
    return result

def write(date: str, city: str, data: dict) -> bool:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "failure"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    success = False
    
    try:
        if BLOB_STORE_URL:
            if not BLOB_READ_WRITE_TOKEN:
                logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot write to Vercel Blob.")
                return False
            
            url = f"https://blob.vercel-storage.com/headlines/{date}/{city}.json"
            headers = {
                "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "Content-Type": "application/json"
            }
            try:
                resp = session.put(url, headers=headers, data=json.dumps(data, indent=2), timeout=3.0)
                resp.raise_for_status()
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error writing cache to Vercel Blob: {e}")
        else:
            path = get_filepath(date, city)
            directory = os.path.dirname(path)
            temp_path = f"{path}.tmp.{uuid.uuid4()}"
            try:
                os.makedirs(directory, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, path)
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_write", details)
        
    return success

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
            session.delete(url, headers=headers, timeout=3.0)
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

def read_top(date: str, city: str) -> dict:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "miss"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    result = {}
    
    try:
        if BLOB_STORE_URL:
            url = get_top_blob_url(date, city)
            try:
                resp = session.get(url, timeout=3.0)
                if resp.status_code == 200:
                    result = resp.json()
                    status = "hit"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error reading top cache from Vercel Blob: {e}")
        else:
            path = get_top_filepath(date, city)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        result = json.load(f)
                        status = "hit"
                except Exception as e:
                    error_class = type(e).__name__
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_read_top", details)
        
    return result

def write_top(date: str, city: str, data: dict) -> bool:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "failure"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    success = False
    
    try:
        if BLOB_STORE_URL:
            if not BLOB_READ_WRITE_TOKEN:
                logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot write to Vercel Blob.")
                return False
            
            url = f"https://blob.vercel-storage.com/top-headlines/{date}/{city}_top.json"
            headers = {
                "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "Content-Type": "application/json"
            }
            try:
                resp = session.put(url, headers=headers, data=json.dumps(data, indent=2), timeout=3.0)
                resp.raise_for_status()
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error writing top cache to Vercel Blob: {e}")
        else:
            path = get_top_filepath(date, city)
            directory = os.path.dirname(path)
            temp_path = f"{path}.tmp.{uuid.uuid4()}"
            try:
                os.makedirs(directory, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, path)
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_write_top", details)
        
    return success

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
            session.delete(url, headers=headers, timeout=3.0)
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


def get_summary_filepath(date: str, city: str, article_id: str) -> str:
    return os.path.join(CACHE_DIR, "summaries", date, city, f"{article_id}.json")


def get_summary_blob_url(date: str, city: str, article_id: str) -> str:
    return f"{BLOB_STORE_URL}/summaries/{date}/{city}/{article_id}.json"


def read_summary(date: str, city: str, article_id: str) -> dict:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "miss"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    result = {}
    
    try:
        if BLOB_STORE_URL:
            url = get_summary_blob_url(date, city, article_id)
            try:
                resp = session.get(url, timeout=3.0)
                if resp.status_code == 200:
                    result = resp.json()
                    status = "hit"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error reading summary cache from Vercel Blob: {e}")
        else:
            path = get_summary_filepath(date, city, article_id)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        result = json.load(f)
                        status = "hit"
                except Exception as e:
                    error_class = type(e).__name__
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "article_id": article_id,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_read_summary", details)
        
    return result


def write_summary(date: str, city: str, article_id: str, data: dict) -> bool:
    import src.telemetry
    import time
    
    start_time = time.perf_counter()
    status = "failure"
    location = "blob" if BLOB_STORE_URL else "local"
    error_class = None
    success = False
    
    try:
        if BLOB_STORE_URL:
            if not BLOB_READ_WRITE_TOKEN:
                logger.warning("BLOB_READ_WRITE_TOKEN is not set; cannot write summary to Vercel Blob.")
                return False
            
            url = f"https://blob.vercel-storage.com/summaries/{date}/{city}/{article_id}.json"
            headers = {
                "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
                "x-api-version": "1",
                "x-add-random-suffix": "0",
                "Content-Type": "application/json"
            }
            try:
                resp = session.put(url, headers=headers, data=json.dumps(data, indent=2), timeout=3.0)
                resp.raise_for_status()
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                logger.warning(f"Error writing summary cache to Vercel Blob: {e}")
        else:
            path = get_summary_filepath(date, city, article_id)
            directory = os.path.dirname(path)
            temp_path = f"{path}.tmp.{uuid.uuid4()}"
            try:
                os.makedirs(directory, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, path)
                success = True
                status = "success"
            except Exception as e:
                error_class = type(e).__name__
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        details = {
            "date": date,
            "city": city,
            "article_id": article_id,
            "status": status,
            "location": location,
            "duration_ms": duration_ms
        }
        if error_class:
            details["error"] = error_class
        src.telemetry.log_event("cache_write_summary", details)
        
    return success


import requests
import random
import threading
from src.telemetry import duration_tracker

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81"
]

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

# Thread-safe session proxy configured at module level for connection pooling
session = ThreadLocalSessionProxy()

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

def set_response_encoding(response):
    # Fallback to UTF-8 if server does not specify a charset or uses default ISO-8859-1
    if not response.encoding or response.encoding.upper() == 'ISO-8859-1':
        response.encoding = 'utf-8'

def fetch_catalog(date_str: str, city_key: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/?json=true&fromDate={date_str}&toDate={date_str}&skipSections=true&os=web&excludePublications=*-*"
    ctx = {"status_code": 0, "date": date_str, "city": city_key}
    with duration_tracker("scraper_fetch_catalog", ctx):
        response = session.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        set_response_encoding(response)
        return response.text

def fetch_cciobjects(issue_id: str, city_key: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/{city_key}/issues/{issue_id}/OPS/cciobjects.json"
    ctx = {"status_code": 0, "issue_id": issue_id, "city": city_key}
    with duration_tracker("scraper_fetch_cciobjects", ctx):
        response = session.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        set_response_encoding(response)
        return response.text

def fetch_article_html(city_key: str, issue_id: str, ref: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/{city_key}/issues/{issue_id}/OPS/{ref}"
    ctx = {"status_code": 0, "issue_id": issue_id, "city": city_key}
    with duration_tracker("scraper_fetch_article_html", ctx):
        response = session.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        set_response_encoding(response)
        return response.text


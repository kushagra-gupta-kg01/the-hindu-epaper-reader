import requests
from src.telemetry import duration_tracker

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

def get_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

def fetch_catalog(date_str: str, city_key: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/?json=true&fromDate={date_str}&toDate={date_str}&skipSections=true&os=web&excludePublications=*-*"
    ctx = {"status_code": 0, "date": date_str, "city": city_key}
    with duration_tracker("scraper_fetch_catalog", ctx):
        response = requests.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text

def fetch_cciobjects(issue_id: str, city_key: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/{city_key}/issues/{issue_id}/OPS/cciobjects.json"
    ctx = {"status_code": 0, "issue_id": issue_id, "city": city_key}
    with duration_tracker("scraper_fetch_cciobjects", ctx):
        response = requests.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text

def fetch_article_html(city_key: str, issue_id: str, ref: str) -> str:
    url = f"https://epaper.thehindu.com/ccidist-ws/th/{city_key}/issues/{issue_id}/OPS/{ref}"
    ctx = {"status_code": 0, "issue_id": issue_id, "city": city_key}
    with duration_tracker("scraper_fetch_article_html", ctx):
        response = requests.get(url, headers=get_headers(), timeout=15)
        ctx["status_code"] = response.status_code
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text


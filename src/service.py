from src import cache
from src import scraper
from src import parser

def get_headlines(date: str, city: str) -> dict:
    # 1. Cache Hit
    if cache.exists(date, city):
        return cache.read(date, city)
        
    # 2. Cache Miss: Fetch & Parse
    catalog_json = scraper.fetch_catalog(date, city)
    issue_id = parser.parse_catalog(catalog_json, city)
    
    cciobjects_json = scraper.fetch_cciobjects(issue_id, city)
    parsed_data = parser.parse_cciobjects(cciobjects_json)
    
    # Preserve the numeric issue ID for URL generation
    parsed_data["issue_id"] = issue_id
    
    # Enrich data with request parameters
    parsed_data["date"] = date
    parsed_data["city"] = city
    
    # Save to local file cache
    cache.write(date, city, parsed_data)
    
    return parsed_data

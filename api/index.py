import re
import os
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src import service
from src import scraper
from src import parser

app = FastAPI(title="The Hindu ePaper Extractor API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_article_id_from_ref(ref: str) -> str:
    # E.g., "GKLG1M8CQ.1+GO1G1NQTF.1.html" or "GKLG1M8CQ.1 GO1G1NQTF.1.html"
    for sep in ["+", " "]:
        if sep in ref:
            part = ref.split(sep)[1]
            if part.endswith(".html"):
                return part[:-5]
            return part
    return ref

@app.get("/api/headlines")
def get_headlines_endpoint(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    city: str = Query(..., description="City ID, e.g. th_delhi")
):
    # Validate date format (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(
            status_code=422,
            detail="Invalid date format. Must be YYYY-MM-DD"
        )
        
    try:
        data = service.get_headlines(date, city)
        return data
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch newspaper data from server: {e}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
        )

@app.get("/api/article")
def get_article_endpoint(
    city: str = Query(..., description="City ID, e.g. th_delhi"),
    issue_id: str = Query(..., description="Issue ID, e.g. 186654"),
    ref: str = Query(..., description="HTML reference file name, e.g. Page+Article.html")
):
    # Re-encode space back to plus for the file server URL
    url_ref = ref.replace(" ", "+")
    
    # Construct article ID from ref
    article_id = get_article_id_from_ref(ref)
    
    try:
        html_content = scraper.fetch_article_html(city, issue_id, url_ref)
        article_data = parser.parse_article(html_content, article_id)
        return article_data
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch article content from server: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
        )

# Resolve absolute path to static directory to ensure compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

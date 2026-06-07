import re
import os
import time
import traceback
import requests
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from src import service
from src import scraper
from src import parser
from src import cache
from src import llm
from src import telemetry
from src.cache import get_ist_today_str

def get_cache_control_headers(date: str) -> dict:
    if date == get_ist_today_str():
        return {"Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400"}
    else:
        return {"Cache-Control": "public, max-age=31536000, immutable"}

ERROR_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate"}

class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry.log_event("request_processed", {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms
            })
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry.log_event("unhandled_exception", {
                "method": method,
                "path": path,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "duration_ms": duration_ms
            })
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers=ERROR_HEADERS
            )

app = FastAPI(title="The Hindu ePaper Extractor API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TelemetryMiddleware)

@app.get("/api/test-unhandled-error")
def test_unhandled_error_endpoint():
    raise RuntimeError("Simulated unhandled exception")

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
    response: Response,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    city: str = Query(..., description="City ID, e.g. th_delhi")
):
    # Validate date format (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(
            status_code=422,
            detail="Invalid date format. Must be YYYY-MM-DD",
            headers=ERROR_HEADERS
        )
        
    try:
        data = service.get_headlines(date, city)
        cc_headers = get_cache_control_headers(date)
        response.headers.update(cc_headers)
        return data
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch newspaper data from server: {e}",
            headers=ERROR_HEADERS
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
            headers=ERROR_HEADERS
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
            headers=ERROR_HEADERS
        )

@app.get("/api/article")
def get_article_endpoint(
    response: Response,
    city: str = Query(..., description="City ID, e.g. th_delhi"),
    issue_id: str = Query(..., description="Issue ID, e.g. 186654"),
    ref: str = Query(..., description="HTML reference file name, e.g. Page+Article.html")
):
    # Validate parameters to block unaligned/unsafe requests
    if not re.match(r"^[a-zA-Z0-9_]+$", city):
        raise HTTPException(
            status_code=422,
            detail="Invalid city format",
            headers=ERROR_HEADERS
        )
    if not re.match(r"^\d+$", issue_id):
        raise HTTPException(
            status_code=422,
            detail="Invalid issue_id format. Must be digits",
            headers=ERROR_HEADERS
        )
    if not re.match(r"^[a-zA-Z0-9_\+\.\s\-]+$", ref):
        raise HTTPException(
            status_code=422,
            detail="Invalid ref format",
            headers=ERROR_HEADERS
        )

    # Re-encode space back to plus for the file server URL
    url_ref = ref.replace(" ", "+")
    
    # Construct article ID from ref
    article_id = get_article_id_from_ref(ref)
    
    try:
        html_content = scraper.fetch_article_html(city, issue_id, url_ref)
        article_data = parser.parse_article(html_content, article_id)
        
        # Set immutable long-term Cache-Control for articles (parsed data is static)
        response.headers.update({"Cache-Control": "public, max-age=31536000, immutable"})
        
        return article_data
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch article content from server: {e}",
            headers=ERROR_HEADERS
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
            headers=ERROR_HEADERS
        )

def normalize_id(art_id: str) -> str:
    if not art_id:
        return ""
    # Strip whitespace, quotes, brackets, and other punctuation
    cleaned = str(art_id).strip()
    if not cleaned:
        return ""
    # Suffix stripping: split on '.' and take the first part
    base = cleaned.split(".")[0]
    # Remove leading/trailing non-alphanumeric characters
    base = re.sub(r'^[^a-zA-Z0-9]+', '', base)
    base = re.sub(r'[^a-zA-Z0-9]+$', '', base)
    return base.strip().lower()

@app.get("/api/top-headlines")
def get_top_headlines_endpoint(
    response: Response,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    city: str = Query(..., description="City ID, e.g. th_delhi"),
    limit: int = Query(None, description="Number of top articles to return"),
    generate: str = Query("false", description="Whether to generate if cache is missing (true/false)")
):
    # Validate date format (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(
            status_code=422,
            detail="Invalid date format. Must be YYYY-MM-DD",
            headers=ERROR_HEADERS
        )

    # Validate limit
    if limit is not None and limit <= 0:
        raise HTTPException(
            status_code=422,
            detail="limit must be a positive integer",
            headers=ERROR_HEADERS
        )

    # Cache hit path
    top_data = cache.read_top(date, city)
    if isinstance(top_data, dict) and top_data.get("status") == "ready":
        if "top_articles" in top_data and limit is not None:
            top_data["top_articles"] = top_data["top_articles"][:limit]
        cc_headers = get_cache_control_headers(date)
        response.headers.update(cc_headers)
        return top_data

    # Cache miss path
    if generate.lower() != "true":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return {"status": "not_generated"}

    # Self-healing main headlines load
    headlines_data = cache.read(date, city)
    if not headlines_data:
        try:
            headlines_data = service.get_headlines(date, city)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e), headers=ERROR_HEADERS)
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Unable to fetch newspaper data from server: {e}", headers=ERROR_HEADERS)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}", headers=ERROR_HEADERS)

    # Count total articles
    all_articles = []
    for page in headlines_data.get("pages", []):
        for art in page.get("articles", []):
            all_articles.append(art)

    if not all_articles:
        raise HTTPException(
            status_code=400,
            detail="No articles available in this edition",
            headers=ERROR_HEADERS
        )

    # Rank headlines using LLM
    rank_limit = min(30, len(all_articles))
    try:
        raw_top_articles = llm.rank_headlines(headlines_data, rank_limit)
    except ValueError as e:
        err_msg = str(e)
        if "OpenRouter API Key is not configured" in err_msg:
            raise HTTPException(status_code=500, detail=err_msg, headers=ERROR_HEADERS)
        else:
            raise HTTPException(status_code=502, detail=f"AI Generation failed: {err_msg}", headers=ERROR_HEADERS)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"AI Generation failed: {e}", headers=ERROR_HEADERS)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Generation failed: {e}", headers=ERROR_HEADERS)

    # Build optimized O(N) lookup index
    lookup = {}
    for art in all_articles:
        art_id = art.get("id")
        if art_id:
            lookup[normalize_id(art_id)] = art

    # Enrich selected articles
    enriched_articles = []
    for item in raw_top_articles:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if not raw_id:
            continue
        norm_id = normalize_id(raw_id)
        if norm_id in lookup:
            original_art = lookup[norm_id]
            ratings_arr = item.get("ratings")
            if not isinstance(ratings_arr, list):
                ratings_arr = [0, 0, 0, 0]
            else:
                # Pad to at least 4 items
                while len(ratings_arr) < 4:
                    ratings_arr.append(0)
                # Parse to integer and clip to 0-10
                cleaned_ratings = []
                for val in ratings_arr[:4]:
                    try:
                        ival = int(val)
                        if ival < 0 or ival > 10:
                            cleaned_ratings.append(0)
                        else:
                            cleaned_ratings.append(ival)
                    except (ValueError, TypeError):
                        cleaned_ratings.append(0)
                ratings_arr = cleaned_ratings

            ratings_dict = {
                "impact": ratings_arr[0],
                "importance": ratings_arr[1],
                "interest": ratings_arr[2],
                "depth": ratings_arr[3]
            }
            enriched_articles.append({
                "id": original_art.get("id"),
                "headline": original_art.get("headline"),
                "html_ref": original_art.get("html_ref"),
                "images": original_art.get("images", []),
                "ratings": ratings_dict,
                "reason": item.get("reason", "")
            })

    if not enriched_articles:
        raise HTTPException(
            status_code=502,
            detail="AI returned an empty selection list",
            headers=ERROR_HEADERS
        )

    # Save unsliced to cache
    top_cache_data = {
        "status": "ready",
        "top_articles": enriched_articles
    }
    cache.write_top(date, city, top_cache_data)

    cc_headers = get_cache_control_headers(date)
    response.headers.update(cc_headers)

    return {
        "status": "ready",
        "top_articles": enriched_articles[:limit] if limit is not None else enriched_articles
    }


@app.get("/_vercel/insights/script.js")
@app.get("/_vercel/speed-insights/script.js")
def mock_vercel_analytics():
    return Response(content="/* Local mock */", media_type="application/javascript")

# Resolve absolute path to static directory to ensure compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

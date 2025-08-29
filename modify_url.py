from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

app = FastAPI(title="Google Custom Search OG Viewer")

# Base URL (constant)
BASE_URL = "https://www.googleapis.com/customsearch/v1?key=AIzaSyCpDbRQOGATgDzaTyI77krM2JPgtwWGG_Y&cx=c7af6f0bf9cd64734&q="

# Daily quota settings
DAILY_LIMIT = 10000   # change to 100 if you are on free tier
USAGE_FILE = "usage_tracker.json"


def load_usage():
    """Load usage data from file or create new if missing."""
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            data = json.load(f)
            data["date"] = datetime.fromisoformat(data["date"]).date()
            return data
    return {"date": datetime.utcnow().date(), "count": 0}


def save_usage(data):
    """Save usage data to file."""
    with open(USAGE_FILE, "w") as f:
        json.dump({"date": str(data["date"]), "count": data["count"]}, f)


usage_tracker = load_usage()


def track_usage(num_queries: int):
    """Track usage per day and reset at midnight UTC."""
    today = datetime.utcnow().date()
    if usage_tracker["date"] != today:
        usage_tracker["date"] = today
        usage_tracker["count"] = 0
    usage_tracker["count"] += num_queries
    save_usage(usage_tracker)  # <-- persist usage
    return DAILY_LIMIT - usage_tracker["count"]


def fetch_h1_tags(url: str):
    """Fetch all H1 tags from a URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        h1_tags = [tag.get_text(strip=True) for tag in soup.find_all("h1")]
        return h1_tags if h1_tags else ["unable to fetch data"]
    except Exception:
        return ["unable to fetch data"]


def extract_relevant_data(items):
    """Extract og:title, og:url, og:description if available + H1 tags."""
    simplified = []
    for item in items:
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [{}])[0]

        og_title = metatags.get("og:title")
        og_url = metatags.get("og:url")
        og_description = metatags.get("og:description")

        if og_title or og_url or og_description:
            url_to_fetch = og_url or item.get("link", "")
            simplified.append({
                "og_title": og_title or "",
                "og_url": url_to_fetch,
                "og_description": og_description or "",
                "h1_tags": fetch_h1_tags(url_to_fetch) if url_to_fetch else ["unable to fetch data"]
            })
        else:
            url_to_fetch = item.get("link", "")
            simplified.append({
                "broken_title": item.get("title", ""),
                "broken_url": url_to_fetch,
                "broken_description": item.get("snippet", ""),
                "h1_tags": fetch_h1_tags(url_to_fetch) if url_to_fetch else ["unable to fetch data"]
            })

    return simplified


def fetch_google_results(query_encoded, total_results):
    """Fetch multiple pages to get more than 10 results."""
    all_items = []
    results_remaining = total_results
    start_index = 1  # Google API is 1-based

    while results_remaining > 0:
        num = min(10, results_remaining)  # max 10 per request
        full_url = BASE_URL + query_encoded + f"&num={num}&start={start_index}"
        response = requests.get(full_url)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        all_items.extend(items)
        results_remaining -= len(items)
        start_index += len(items)

    return all_items


# POST endpoint
@app.post("/get-json")
async def get_json_post(query: str = Form(...), num_results: int = Form(10)):
    if num_results > 100:
        return JSONResponse(status_code=400, content={"error": "Maximum allowed results is 100"})
    query_encoded = query.replace(" ", "%20")
    try:
        items = fetch_google_results(query_encoded, num_results)
        simplified_data = extract_relevant_data(items)
        limit_left = track_usage(len(items))   # now persisted in file

        return JSONResponse(content={
            "limit_left_today": max(limit_left, 0),
            "results": simplified_data
        })
    except requests.exceptions.RequestException:
        return JSONResponse(status_code=400, content={"error": "unable to fetch data"})

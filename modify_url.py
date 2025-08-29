from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="Google Custom Search OG Viewer")

# Base URL (constant)
BASE_URL = "https://www.googleapis.com/customsearch/v1?key=AIzaSyCpDbRQOGATgDzaTyI77krM2JPgtwWGG_Y&cx=c7af6f0bf9cd64734&q="

def extract_relevant_data(items):
    """Extract og:title, og:url, og:description if available; else show broken_* only."""
    simplified = []
    for item in items:
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [{}])[0]

        og_title = metatags.get("og:title")
        og_url = metatags.get("og:url")
        og_description = metatags.get("og:description")

        if og_title or og_url or og_description:
            # If OG tags exist, return only OG keys
            simplified.append({
                "og_title": og_title or "",
                "og_url": og_url or "",
                "og_description": og_description or ""
            })
        else:
            # If no OG tags, return only broken_* keys
            simplified.append({
                "broken_title": item.get("title", ""),
                "broken_url": item.get("link", ""),
                "broken_description": item.get("snippet", "")
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

# POST endpoint (simplified OG/broken data)
@app.post("/get-json")
async def get_json_post(query: str = Form(...), num_results: int = Form(10)):
    if num_results > 100:
        return JSONResponse(status_code=400, content={"error": "Maximum allowed results is 100"})
    query_encoded = query.replace(" ", "%20")
    try:
        items = fetch_google_results(query_encoded, num_results)
        simplified_data = extract_relevant_data(items)
        return JSONResponse(content=simplified_data)
    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


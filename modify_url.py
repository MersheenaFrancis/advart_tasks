from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="Google Custom Search Multi-Result Viewer")

BASE_URL = "https://www.googleapis.com/customsearch/v1?key=AIzaSyCpDbRQOGATgDzaTyI77krM2JPgtwWGG_Y&cx=c7af6f0bf9cd64734&q="

def extract_relevant_data(items):
    """Extract only title, link, snippet from items."""
    simplified = []
    for item in items:
        simplified.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "description": item.get("snippet")
        })
    return simplified

def fetch_google_results(query, total_results):
    """Fetch multiple pages to get more than 10 results."""
    all_results = []
    results_remaining = total_results
    start_index = 1  # Google API is 1-based
    
    while results_remaining > 0:
        # Google allows max 10 results per request
        num = min(10, results_remaining)
        full_url = f"{BASE_URL}{query}&num={num}&start={start_index}"
        response = requests.get(full_url)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        simplified = extract_relevant_data(items)
        all_results.extend(simplified)
        results_remaining -= len(simplified)
        start_index += len(simplified)
    
    return all_results

# POST endpoint
@app.post("/get-json")
async def get_json_post(query: str = Form(...), num_results: int = Form(10)):
    if num_results > 100:
        return JSONResponse(status_code=400, content={"error": "Maximum results allowed is 100."})
    
    query_encoded = query.replace(" ", "%20")
    try:
        results = fetch_google_results(query_encoded, num_results)
        return JSONResponse(content=results)
    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=400, content={"error": str(e)})



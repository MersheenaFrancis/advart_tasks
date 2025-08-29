from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from utils import fetch_google_results, extract_relevant_data, track_usage, usage_tracker
from datetime import datetime

app = FastAPI(title="Google Custom Search OG Viewer")


@app.post("/get-json")
async def get_json_post(query: str = Form(...), num_results: int = Form(10)):
    if num_results > 100:
        return JSONResponse(status_code=400, content={"error": "Maximum allowed results is 100"})

    today = datetime.utcnow().date()
    if usage_tracker["date"] != today:
        usage_tracker["date"] = today
        usage_tracker["count"] = 0

    if usage_tracker["count"] >= 10000:  # daily limit
        return JSONResponse(status_code=403, content={"error": "you have reached the limit"})

    query_encoded = query.replace(" ", "%20")
    try:
        items = fetch_google_results(query_encoded, num_results)
        simplified_data = extract_relevant_data(items)
        limit_left = track_usage(len(items))

        return JSONResponse(content={
            "limit_left_today": max(limit_left, 0),
            "results": simplified_data
        })
    except Exception:
        return JSONResponse(status_code=400, content={"error": "unable to fetch data"})

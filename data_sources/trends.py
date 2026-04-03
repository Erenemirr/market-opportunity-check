import os
import requests

"""
    Fetches Google Trends timeline data reliably using SerpApi (bypassing the older 429 timeouts).
    Returns the summary momentum and the raw timeline JSON data for Streamlit line charts.
"""

def fetch_trends_data(keyword: str, timeframe: str = "today 3-m", geo: str = "") -> dict:
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return {"status": "missing_key", "error_message": "Missing SERPAPI_API_KEY in .env", "momentum": "N/A", "trend_direction": "UNKNOWN", "chart_data": {}}

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_trends",
        "q": keyword,
        "api_key": api_key,
        "data_type": "TIMESERIES",
        "date": timeframe
    }
    # If the user selected a specific country, inject the Geo filter!
    if geo:
        params["geo"] = geo

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        timeline = data.get("interest_over_time", {}).get("timeline_data", [])
        if not timeline:
            return {"status": "no_data", "momentum": "0%", "trend_direction": "FLAT", "chart_data": {}}
        
        chart_data = {}
        values = []
        for item in timeline:
            date = item.get("date")
            val_obj = item.get("values", [{}])[0]
            val = val_obj.get("extracted_value", 0)
            
            if date:
                chart_data[date] = val
            values.append(val)
            
        recent = sum(values[-4:]) / 4 if len(values) >= 4 else values[-1]
        old = sum(values[:4]) / 4 if len(values) >= 4 else values[0]
        
        diff = recent - old
        momentum = f"{'+' if diff >= 0 else ''}{diff:.1f}%"
        direction = "UP" if diff > 5 else "DOWN" if diff < -5 else "FLAT"
        
        return {
            "status": "success",
            "momentum": momentum,
            "trend_direction": direction,
            "chart_data": chart_data 
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e), "momentum": "0%", "trend_direction": "UNKNOWN", "chart_data": {}}

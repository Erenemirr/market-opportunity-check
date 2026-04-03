import os
import requests

"""
    Fetches search and news snippets from Serper.dev API.

"""

def fetch_serper_data(query: str, country_code: str = 'us') -> dict:
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return {"status": "missing_key", "error_message": "Invalid or missing SERPER_API_KEY.", "snippets": [], "related_searches": []}
        
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "gl": country_code,
        "hl": "en",
        "num": 5
    }
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        organic_results = data.get("organic", [])
        snippets = [f"{item.get('title')}: {item.get('snippet')}" for item in organic_results]
        
        return {
            "status": "success",
            "snippets": snippets,
            "related_searches": [rs.get("query") for rs in data.get("relatedSearches", [])][:5]
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e), "snippets": []}

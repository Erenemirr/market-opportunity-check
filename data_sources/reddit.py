import os
import requests

"""
    Searches Reddit and Quora for complaints, issues, or reviews 
    bypassing official APIs by using Serper advanced Google Search.
"""

def fetch_reddit_complaints(product: str, limit: int = 5) -> dict:
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return {"status": "missing_key", "error_message": "Invalid or missing SERPER_API_KEY.", "posts": [], "count": 0}
        
    url = "https://google.serper.dev/search"
    ## Using 'site:' operator to force Google to only look at reddit/quora
    advanced_query = f'(site:reddit.com OR site:quora.com) "{product}" (issue OR problem OR complaint OR review)'
    
    payload = {
        "q": advanced_query,
        "num": limit
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
        posts = []
        for item in organic_results:
            posts.append({
                "title": item.get('title'),
                "text": item.get('snippet'),
                "link": item.get('link')
            })
            
        return {
            "status": "success",
            "posts": posts,
            "count": len(posts)
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e), "posts": []}

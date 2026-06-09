import os
import json
import requests
from datetime import datetime

def fetch_realtime_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        raise ValueError("❌ [FATAL] SEARCHAPI_API_KEY is missing.")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚙️ Viral Matrix Engine: Fetching US Trends...")

    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        raw_trends = (
            data.get("trends") or
            data.get("trending_searches") or
            data.get("trending_queries") or
            []
        )

        print(f"📡 Raw Data Ingested: {len(raw_trends)} trends found.")

        # 黑名單過濾
        blacklist = ["vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league", "weather", "stock", "market", "espn"]
        
        cleaned_list = []
        for item in raw_trends:
            query = item.get("query", "").strip()
            if not query:
                continue
                
            query_lower = query.lower()
            if any(word in query_lower for word in blacklist):
                continue
            if "sports" in [c.lower() for c in item.get("categories", [])]:
                continue

            cleaned_list.append({
                "query": query,
                "search_volume": item.get("search_volume", 0),
                "increase": item.get("percentage_increase", 0) or 0,
                "news_token": item.get("news_token")
            })

        # === 重要優化：按價值排序 ===
        cleaned_list.sort(key=lambda x: (x["increase"], x["search_volume"]), reverse=True)

        # 取 Top 80（比之前 30 多，但 Generator 會自己決定用幾多）
        top_trends = cleaned_list[:80]

        output_data = {
            "matrix_metadata": {
                "strategy": "US Market Optimized",
                "daily_target": 1200,           # Generator 實際目標
                "active_hours": 8,
                "config": {
                    "keywords_count": len(top_trends),
                    "last_updated_hkt": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            },
            "trending_seeds": top_trends
        }

        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Success! Generated Top {len(top_trends)} high-value trends.")
        
    except Exception as e:
        print(f"⚠️ Runtime Error: {e}")
        raise


if __name__ == "__main__":
    fetch_realtime_trends()

import os
import json
import requests
from datetime import datetime

def fetch_realtime_trends():
    # 1. 讀取 API Key
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        raise ValueError("❌ [FATAL] SEARCHAPI_API_KEY is missing. Check GitHub Secrets.")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚙️ Viral Matrix Engine: Starting...")

    # 2. SearchApi 設定
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            response.raise_for_status()

        data = response.json()
        
        # 兼容多種 API 回傳路徑
        raw_trends = (
            data.get("trends") or 
            data.get("trending_searches") or 
            data.get("trending_queries") or 
            []
        )
        
        print(f"📡 Raw Data Ingested: {len(raw_trends)} potential targets found.")

        # 3. 強化版黑名單 (剔除無效點擊流量)
        blacklist = [
            "vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league",
            "weather", "forecast", "radar", "temperature", "rain", "snow",
            "espn", "stock", "market", "nasdaq"
        ]

        # 4. 過濾與清洗
        cleaned_list = []
        for item in raw_trends:
            query = item.get("query", "")
            query_lower = query.lower()
            categories = [c.lower() for c in item.get("categories", [])]

            if any(word in query_lower for word in blacklist):
                continue
            if "sports" in categories:
                continue
            
            cleaned_list.append({
                "query": query,
                "search_volume": item.get("search_volume", "N/A"),
                "increase": item.get("percentage_increase", 0),
                "news_token": item.get("news_token")
            })

        # 5. 【Click Farm 核心配置】取 Top 30 擴大撒網面
        top_30_trends = cleaned_list[:30]

        # 6. 輸出矩陣清單
        # 設定：30 關鍵字 * 20 變體 = 600 篇/每小時
        output_data = {
            "matrix_metadata": {
                "strategy": "Long-tail Harvest",
                "daily_target": 10800,  # 18 hours * 600
                "active_hours": 18,
                "config": {
                    "keywords_count": len(top_30_trends),
                    "articles_per_keyword": 20,
                    "total_this_batch": len(top_30_trends) * 20
                },
                "last_updated_hkt": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "trending_seeds": top_30_trends
        }

        # 7. 寫入 JSON
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Success! Generated {len(top_30_trends)} seeds for the next 600 articles.")
        print(f"📁 master_trends.json is ready for the Writing Engine.")

    except Exception as e:
        print(f"⚠️ Runtime Error: {e}")
        raise

if __name__ == "__main__":
    fetch_realtime_trends()

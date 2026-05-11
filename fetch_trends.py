import os
import json
import requests
from datetime import datetime

def fetch_realtime_trends():
    # 1. 讀取 API Key (GitHub Action 透過 env 傳入)
    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        raise ValueError("❌ 找不到 SEARCHAPI_API_KEY！請檢查 GitHub Secrets 及 YAML env 設定。")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 開始抓取數據...")

    # 2. 設定 SearchApi 參數
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params)
        
        # 如果出錯 (如 401, 403)，直接印出 API 回傳的錯誤內容
        if response.status_code != 200:
            print(f"❌ API 報錯！狀態碼: {response.status_code}")
            print(f"回傳內容: {response.text}")
            response.raise_for_status()

        data = response.json()
        
        # 兼容性獲取數據列表
        trends_list = (
            data.get("trends") or 
            data.get("trending_searches") or 
            data.get("trending_queries") or 
            []
        )
        
        print(f"📡 API 原始回傳量: {len(trends_list)} 條")

        # 3. 定義過濾名單 (體育 + 天氣)
        sports_blacklist = [
            "vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league",
            "playoffs", "highlights", "recap", "match", "cup", "tournament",
            "warriors", "lakers", "celtics", "yankees", "dodgers", "espn"
        ]
        weather_blacklist = [
            "weather", "forecast", "radar", "temperature", "rain", 
            "snow", "storm", "hurricane", "typhoon", "humidity", "degree"
        ]
        full_blacklist = sports_blacklist + weather_blacklist

        # 4. 執行過濾與整理數據
        filtered_results = []
        for item in trends_list:
            query = item.get("query", "")
            query_lower = query.lower()
            categories = [c.lower() for c in item.get("categories", [])]

            # 檢查黑名單與分類
            is_blacklisted_keyword = any(word in query_lower for word in full_blacklist)
            is_sports_category = "sports" in categories
            
            if is_blacklisted_keyword or is_sports_category:
                continue
            
            # 整理格式
            filtered_results.append({
                "position": item.get("position"),
                "query": query,
                "search_volume": item.get("search_volume"),
                "percentage_increase": item.get("percentage_increase"),
                "category": item.get("categories", []),
                "is_active": item.get("is_active", False),
                "news_token": item.get("news_token"),
                "fetched_at": datetime.now().isoformat()
            })

        # 5. 儲存到 master_trends.json
        output = {
            "last_updated": datetime.now().isoformat(),
            "count": len(filtered_results),
            "trends": filtered_results
        }

        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"✅ 過濾完成！剩餘: {len(filtered_results)} 條")
        print(f"📁 master_trends.json 已更新。")

    except Exception as e:
        print(f"⚠️ 執行過程中發生錯誤: {e}")
        # 在 GitHub Actions 中，我們希望報錯時流程會停止，所以可以選擇 raise
        raise

if __name__ == "__main__":
    fetch_realtime_trends()

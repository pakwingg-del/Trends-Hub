import requests
import json

def fetch_google_trends(api_key, geo="US", timeframe="past_24_hours"):
    url = "https://www.searchapi.io/api/v1/search"
    
    params = {
        "engine": "google_trends_trending_now",
        "geo": geo,
        "time": timeframe,
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # 檢查 API 是否調用成功
        data = response.json()
        
        # 提取我們核心需要的趨勢清單
        trends = data.get("trends", [])
        
        # 轉換成你網頁前端更好用的格式
        processed_news = []
        for item in trends:
            processed_news.append({
                "rank": item.get("position"),
                "title": item.get("query"),
                "volume": item.get("search_volume"),
                "growth": f"{item.get('percentage_increase')}%",
                "tags": item.get("categories", []),
                "is_hot": item.get("is_active", False)
            })
            
        return processed_news

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

# 測試用
if __name__ == "__main__":
    MY_KEY = "你的_API_KEY"
    results = fetch_google_trends(MY_KEY)
    print(json.dumps(results[:5], indent=2)) # 只印出前 5 條

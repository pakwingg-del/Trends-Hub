import requests
import json
import os
from datetime import datetime

def fetch_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    # 確保 URL 是正確的 V1 入口
    url = "https://www.searchapi.io/api/v1/search"
    
    params = {
        "engine": "google_trends",
        "data_type": "trending_searches",
        "api_key": api_key,
        "geo": "US"
    }
    
    print(f"正在發送請求到 SearchAPI... Key 前四位: {api_key[:4] if api_key else 'None'}")
    
    try:
        response = requests.get(url, params=params)
        
        # --- 關鍵：印出原始回應內容 ---
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Raw Response: {response.text[:500]}") # 印出前 500 個字睇吓報咩錯
        
        data = response.json()
        
        # 嘗試從不同欄位抓取資料
        # 1. 實時趨勢 2. 每日趨勢 3. 或者是 Top Queries
        raw_trends = data.get("trending_searches", [])
        if not raw_trends:
            raw_trends = data.get("daily_searches", [])
        if not raw_trends:
            # 有些版本會包在 google_trends 裡面
            raw_trends = data.get("google_trends", {}).get("trending_searches", [])

        master_trends = []
        for item in raw_trends:
            # 兼容 query 或 title 格式
            topic = item.get("query") or item.get("title")
            if topic:
                master_trends.append({
                    "topic": topic,
                    "search_volume": item.get("search_volume", "Trending"),
                    "snippet": item.get("snippet", "Latest viral updates."),
                    "timestamp": datetime.now().isoformat()
                })
            
        output = {
            "last_updated": datetime.now().isoformat(),
            "count": len(master_trends),
            "trends": master_trends
        }
        
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 完成！抓取到 {len(master_trends)} 條話題。")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")

if __name__ == "__main__":
    fetch_trends()

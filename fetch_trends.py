import requests
import json
import os
from datetime import datetime

def fetch_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    url = "https://www.searchapi.io/api/v1/search"
    
    # 根據官方 400 Error 回饋，data_type 必須係 trends
    params = {
        "engine": "google_trends",
        "data_type": "trends",  # 呢個係關鍵！
        "api_key": api_key,
        "geo": "US"
    }
    
    print(f"正在發送請求到 SearchAPI (2026 最終修正版)...")
    
    try:
        response = requests.get(url, params=params)
        print(f"HTTP Status Code: {response.status_code}")
        
        # 如果仲係 400，印出原因睇清楚
        if response.status_code != 200:
            print(f"Error Body: {response.text}")
            return

        data = response.json()
        
        # 抓取 trends 陣列
        trends_list = data.get("trends", [])
        
        master_trends = []
        for item in trends_list:
            topic = item.get("query")
            if topic:
                master_trends.append({
                    "topic": topic,
                    "search_volume": item.get("search_volume", "Trending"),
                    "snippet": f"Viral trend spotted in US. Search volume is {item.get('search_volume', 'rising')}.",
                    "timestamp": datetime.now().isoformat()
                })
            
        output = {
            "last_updated": datetime.now().isoformat(),
            "count": len(master_trends),
            "trends": master_trends
        }
        
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 成功！抓取到 {len(master_trends)} 條話題。")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")

if __name__ == "__main__":
    fetch_trends()

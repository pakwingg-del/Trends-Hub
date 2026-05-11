import requests
import json
import os
from datetime import datetime

def fetch_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    url = "https://www.searchapi.io/api/v1/search"
    
    # 修正：data_type 依家要用 "trends" 或者唔寫由佢 default
    params = {
        "engine": "google_trends",
        "api_key": api_key,
        "geo": "US"
    }
    
    print(f"正在發送請求到 SearchAPI (修正版)...")
    
    try:
        response = requests.get(url, params=params)
        print(f"HTTP Status Code: {response.status_code}")
        
        data = response.json()
        
        # SearchAPI 最新回傳結構通常喺 'trends' 呢個 key 入面
        trends_list = data.get("trends", [])
        
        master_trends = []
        for item in trends_list:
            # 攞話題名
            topic = item.get("query")
            if topic:
                master_trends.append({
                    "topic": topic,
                    "search_volume": item.get("search_volume", "Trending"),
                    "snippet": f"Viral trend with {item.get('search_volume', 'rising')} searches.",
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

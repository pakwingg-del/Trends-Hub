import os
import json
import requests
from datetime import datetime

SEARCHAPI_KEY = os.environ.get("SEARCHAPI_API_KEY")

def fetch_and_save():
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_trends",
        "data_type": "trending_searches",
        "api_key": SEARCHAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        trends = data.get("trending_searches", [])
        
        # 存檔供其他 Repo 讀取
        output = {
            "last_updated": datetime.now().isoformat(),
            "count": len(trends),
            "trends": trends
        }
        
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            
        print(f"✅ 成功採集 {len(trends)} 條趨勢")
        
    except Exception as e:
        print(f"❌ 採集失敗: {e}")

if __name__ == "__main__":
    fetch_and_save()

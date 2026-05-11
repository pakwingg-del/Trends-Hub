import requests
import json
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def fetch_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    url = "https://www.searchapi.io/api/v1/search"
    
    # 設定重試策略：如果遇到 500, 502, 503, 504，會自動隔一段時間再試，最多試 3 次
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    params = {
        "engine": "google_trends",
        "data_type": "RELATED_QUERIES",
        "cat": "0",       
        "geo": "US",      # 鎖定一個區域通常比較穩定
        "api_key": api_key
    }
    
    print(f"正在發送請求到 SearchAPI (強化穩定版)...")
    
    try:
        # 加埋 timeout 防止 GitHub Action 等到天荒地老
        response = session.get(url, params=params, timeout=30)
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 伺服器回報錯誤: {response.text}")
            return

        data = response.json()
        rising_queries = data.get("related_queries", {}).get("rising", [])
        
        if not rising_queries:
            print("⚠️ 雖然 API 成功，但呢一刻冇 Rising Trends。")
            return

        master_trends = []
        for item in rising_queries:
            master_trends.append({
                "topic": item.get("query"),
                "value": item.get("extracted_value"),
                "timestamp": datetime.now().isoformat()
            })
            
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump({"trends": master_trends, "updated_at": datetime.now().isoformat()}, f, indent=2)
            
        print(f"✅ 成功更新 {len(master_trends)} 條話題！")
            
    except Exception as e:
        print(f"❌ 連線失敗: {str(e)}")

if __name__ == "__main__":
    fetch_trends()

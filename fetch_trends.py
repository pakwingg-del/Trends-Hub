import requests
import json
import os
from datetime import datetime

def fetch_trends():
    api_key = os.getenv("SEARCHAPI_API_KEY")
    url = "https://www.searchapi.io/api/v1/search"
    
    # 根據文檔，要攞整體熱搜，用 RELATED_QUERIES 唔加 q，但加 cat
    params = {
        "engine": "google_trends",
        "data_type": "RELATED_QUERIES",
        "cat": "0",       # 0 代表所有類別
        "geo": "US",      # 你可以改做 HK 試吓
        "api_key": api_key
    }
    
    print(f"正在發送請求到 SearchAPI (文檔修正版)...")
    
    try:
        response = requests.get(url, params=params)
        print(f"HTTP Status Code: {response.status_code}")
        
        data = response.json()
        
        if response.status_code != 200:
            print(f"API Error: {data.get('error', 'Unknown error')}")
            return

        # 文檔顯示資料會喺 related_queries -> rising 入面
        # 呢啲 "Rising" 嘅話題先至係最「爆」嘅
        rising_queries = data.get("related_queries", {}).get("rising", [])
        top_queries = data.get("related_queries", {}).get("top", [])
        
        # 優先攞 Rising，再用 Top 補位
        raw_list = rising_queries + top_queries
        
        master_trends = []
        for item in raw_list:
            query_text = item.get("query")
            if query_text:
                master_trends.append({
                    "topic": query_text,
                    "search_volume": item.get("values", "Rising"), # 會顯示 "Breakout" 或數值
                    "link": item.get("link", ""),
                    "timestamp": datetime.now().isoformat()
                })
            
        output = {
            "last_updated": datetime.now().isoformat(),
            "count": len(master_trends),
            "trends": master_trends
        }
        
        with open("master_trends.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 成功！抓取到 {len(master_trends)} 條趨勢話題。")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")

if __name__ == "__main__":
    fetch_trends()

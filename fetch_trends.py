import os
import json
import argparse
import requests
from datetime import datetime

# ====================== 每個「產品」定義 ======================
# categories: SearchAPI google_trends_trending_now 支援嘅分類
SOURCES = [
    {
        "id": "general",
        "output": "master_trends.json",
        "categories": ["all"],
        "top_n": 100,
        "blacklist_extra": [],
    },
    {
        "id": "finance",
        "output": "trends_finance.json",
        "categories": ["business_and_finance", "shopping"],
        "top_n": 80,
        # finance 唔好 ban 死 stock/market
        "blacklist_extra": ["nba", "nfl", "mlb", "score", "taylor swift", "kardashian"],
    },
    {
        "id": "tech",
        "output": "trends_tech.json",
        "categories": ["technology"],
        "top_n": 80,
        "blacklist_extra": ["nba", "nfl", "mlb", "score", "divorce", "wedding"],
    },
    {
        "id": "entertainment",
        "output": "trends_entertainment.json",
        "categories": ["entertainment", "beauty_and_fashion"],
        "top_n": 80,
        "blacklist_extra": ["nba", "nfl", "mlb", "stock", "mortgage", "bitcoin"],
    },
]

# 共用黑名單（體育／天氣等）
BASE_BLACKLIST = [
    "vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league",
    "weather", "forecast", "radar", "espn",
]

def fetch_category(api_key: str, category: str) -> list:
    """拉單一 category 嘅 trending now"""
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "api_key": api_key,
    }
    # all = 唔傳 category（同舊行為）
    if category and category != "all":
        params["category"] = category

    print(f"  🔎 Fetching category={category} ...")
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ API {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()

    data = resp.json()
    raw = (
        data.get("trends")
        or data.get("trending_searches")
        or data.get("trending_queries")
        or []
    )
    print(f"  📡 {category}: {len(raw)} raw trends")
    return raw

def clean_trends(raw_trends: list, blacklist_extra: list) -> list:
    blacklist = [w.lower() for w in (BASE_BLACKLIST + (blacklist_extra or []))]
    cleaned = []
    seen = set()

    for item in raw_trends:
        query = (item.get("query") or "").strip()
        if not query:
            continue
        q_lower = query.lower()
        if q_lower in seen:
            continue
        if any(word in q_lower for word in blacklist):
            continue

        cats = [str(c).lower() for c in (item.get("categories") or [])]
        if "sports" in cats:
            continue

        seen.add(q_lower)
        cleaned.append({
            "query": query,
            "search_volume": item.get("search_volume", 0) or 0,
            "increase": item.get("percentage_increase", 0) or 0,
            "categories": item.get("categories") or [],
            "news_token": item.get("news_token"),
        })

    cleaned.sort(key=lambda x: (x["increase"], x["search_volume"]), reverse=True)
    return cleaned

def build_one_source(api_key: str, source: dict) -> dict:
    print(f"\n{'='*50}")
    print(f"🏭 Building source: {source['id']} → {source['output']}")
    print(f"{'='*50}")

    all_raw = []
    for cat in source["categories"]:
        try:
            all_raw.extend(fetch_category(api_key, cat))
        except Exception as e:
            print(f"  ⚠️ Skip category {cat}: {e}")

    cleaned = clean_trends(all_raw, source.get("blacklist_extra", []))
    top_n = int(source.get("top_n", 80))
    top_trends = cleaned[:top_n]

    output_data = {
        "matrix_metadata": {
            "source_id": source["id"],
            "categories": source["categories"],
            "strategy": "Category-targeted US trends",
            "config": {
                "keywords_count": len(top_trends),
                "last_updated_hkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        },
        "trending_seeds": top_trends,
    }

    with open(source["output"], "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote {source['output']} — {len(top_trends)} seeds")
    if top_trends[:5]:
        print("   Sample:", ", ".join(t["query"] for t in top_trends[:5]))
    return output_data

def main():
    parser = argparse.ArgumentParser(description="Fetch categorized Google Trends via SearchAPI")
    parser.add_argument(
        "--id",
        default=None,
        help="Only build one source id, e.g. finance / tech / entertainment / general",
    )
    args = parser.parse_args()

    api_key = os.getenv("SEARCHAPI_API_KEY")
    if not api_key:
        raise ValueError("❌ [FATAL] SEARCHAPI_API_KEY is missing.")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Trends Hub starting...")

    targets = SOURCES
    if args.id:
        targets = [s for s in SOURCES if s["id"] == args.id]
        if not targets:
            raise SystemExit(f"❌ Unknown source id: {args.id}")

    for source in targets:
        build_one_source(api_key, source)

    print("\n🎉 All requested trend files updated.")

if __name__ == "__main__":
    main()

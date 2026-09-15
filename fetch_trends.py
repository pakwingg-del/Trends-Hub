import os
import json
import argparse
import requests
from datetime import datetime

# SerpAPI google_trends_trending_now category_id map
# https://serpapi.com/google-trends-trending-now-categories
CATEGORY_IDS = {
    "all": None,
    "business_and_finance": 3,
    "shopping": 16,
    "technology": 18,
    "entertainment": 4,
    "beauty_and_fashion": 2,
}

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

BASE_BLACKLIST = [
    "vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league",
    "weather", "forecast", "radar", "espn",
]


def fetch_category(api_key: str, category: str) -> list:
    """Fetch trending now for one category via SerpAPI."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "hours": 24,
        "api_key": api_key,
    }
    category_id = CATEGORY_IDS.get(category)
    if category_id is not None:
        params["category_id"] = category_id

    print(f"  -> Fetching category={category} (id={category_id}) ...")
    resp = requests.get(url, params=params, timeout=45)
    if resp.status_code != 200:
        print(f"  !! API {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()

    data = resp.json()
    raw = (
        data.get("trending_searches")
        or data.get("trends")
        or data.get("trending_queries")
        or []
    )
    print(f"  OK {category}: {len(raw)} raw trends")
    return raw


def normalize_categories(raw_cats) -> list:
    """Keep category names as strings for content-factory compatibility."""
    out = []
    if not raw_cats:
        return out
    for c in raw_cats:
        if isinstance(c, dict):
            name = c.get("name") or ""
            if name:
                out.append(str(name).lower().replace(" ", "_"))
        else:
            out.append(str(c).lower())
    return out


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

        cats = normalize_categories(item.get("categories") or [])
        if "sports" in cats:
            continue

        increase = (
            item.get("increase_percentage")
            if item.get("increase_percentage") is not None
            else item.get("percentage_increase", 0)
        ) or 0
        volume = item.get("search_volume", 0) or 0
        # SerpAPI sometimes returns strings like "200K+"
        if isinstance(volume, str):
            digits = "".join(ch for ch in volume if ch.isdigit())
            volume = int(digits) if digits else 0
            if "k" in str(item.get("search_volume", "")).lower() and volume < 1000:
                volume *= 1000
            if "m" in str(item.get("search_volume", "")).lower() and volume < 1000000:
                volume *= 1000000

        seen.add(q_lower)
        cleaned.append({
            "query": query,
            "search_volume": volume,
            "increase": increase,
            "categories": cats,
            "news_token": item.get("news_page_token") or item.get("news_token"),
        })

    cleaned.sort(key=lambda x: (x["increase"], x["search_volume"]), reverse=True)
    return cleaned


def build_one_source(api_key: str, source: dict) -> dict:
    print(f"\n{'=' * 50}")
    print(f"Building source: {source['id']} -> {source['output']}")
    print(f"{'=' * 50}")

    all_raw = []
    for cat in source["categories"]:
        try:
            all_raw.extend(fetch_category(api_key, cat))
        except Exception as e:
            print(f"  !! Skip category {cat}: {e}")

    cleaned = clean_trends(all_raw, source.get("blacklist_extra", []))
    top_n = int(source.get("top_n", 80))
    top_trends = cleaned[:top_n]

    output_data = {
        "matrix_metadata": {
            "source_id": source["id"],
            "categories": source["categories"],
            "strategy": "Category-targeted US trends via SerpAPI",
            "provider": "serpapi",
            "config": {
                "keywords_count": len(top_trends),
                "last_updated_hkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        },
        "trending_seeds": top_trends,
    }

    with open(source["output"], "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {source['output']} -> {len(top_trends)} seeds")
    if top_trends[:5]:
        print("   Sample:", ", ".join(t["query"] for t in top_trends[:5]))
    return output_data


def main():
    parser = argparse.ArgumentParser(description="Fetch categorized Google Trends via SerpAPI")
    parser.add_argument(
        "--id",
        default=None,
        help="Only build one source id, e.g. finance / tech / entertainment / general",
    )
    args = parser.parse_args()

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("[FATAL] SERPAPI_API_KEY is missing.")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Trends Hub starting (SerpAPI)...")

    targets = SOURCES
    if args.id:
        targets = [s for s in SOURCES if s["id"] == args.id]
        if not targets:
            raise SystemExit(f"Unknown source id: {args.id}")

    for source in targets:
        build_one_source(api_key, source)

    print("\nAll requested trend files updated.")


if __name__ == "__main__":
    main()

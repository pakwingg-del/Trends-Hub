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
    "games": 6,
    "science": 15,
}

# Niche sources often have thin category pools in a 24h window.
# Strategy: wider lookback + sibling categories + keyword scoop from "all".
SOURCES = [
    {
        "id": "general",
        "output": "master_trends.json",
        "categories": ["all"],
        "hours": [24],
        "top_n": 100,
        "blacklist_extra": [],
        "keyword_include": [],
        "scoop_from_all": False,
    },
    {
        "id": "finance",
        "output": "trends_finance.json",
        "categories": ["business_and_finance", "shopping"],
        "hours": [24, 168],
        "top_n": 80,
        "blacklist_extra": ["nba", "nfl", "mlb", "score", "taylor swift", "kardashian"],
        "keyword_include": [
            "price", "prices", "inflation", "grocery", "walmart", "target", "costco",
            "mortgage", "rent", "interest", "fed", "credit card", "debt", "budget",
            "deal", "discount", "layoff", "gas", "stock", "market", "bank", "fed ",
            "retail", "airline", "crypto", "bitcoin", "trading", "dow", "nasdaq", "s&p",
        ],
        "scoop_from_all": True,
    },
    {
        "id": "tech",
        "output": "trends_tech.json",
        # Technology alone is often <10 in 24h; games/science + 7-day window help.
        "categories": ["technology", "games", "science"],
        "hours": [24, 168],
        "top_n": 80,
        "blacklist_extra": ["nba", "nfl", "mlb", "score", "divorce", "wedding", "lottery"],
        "keyword_include": [
            "iphone", "android", "samsung", "google", "pixel", "laptop", "macbook",
            "ipad", "airpods", "headphones", "gadget", "smartphone", "wearable",
            "smart home", "nvidia", "gpu", "launch", "leak", "firmware", "update",
            "review", "apple", "chatgpt", "openai", "ai ", " app", "ios", "outage",
            "steam", "xbox", "playstation", "ps5", "ps6", "software", "chip", "intel",
            "amd", "microsoft", "windows", "tesla", "robot", "drone", "vr", "meta quest",
        ],
        "scoop_from_all": True,
    },
    {
        "id": "entertainment",
        "output": "trends_entertainment.json",
        "categories": ["entertainment", "beauty_and_fashion"],
        "hours": [24],
        "top_n": 80,
        "blacklist_extra": ["nba", "nfl", "mlb", "stock", "mortgage", "bitcoin"],
        "keyword_include": [],
        "scoop_from_all": False,
    },
]

BASE_BLACKLIST = [
    "vs", "score", "nba", "mlb", "nfl", "nhl", "fifa", "premier league",
    "weather", "forecast", "radar", "espn",
]


def fetch_category(api_key: str, category: str, hours: int) -> list:
    """Fetch trending now for one category + lookback window via SerpAPI."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "hl": "en",
        "hours": hours,
        "api_key": api_key,
    }
    category_id = CATEGORY_IDS.get(category)
    if category_id is not None:
        params["category_id"] = category_id

    print(f"  -> Fetching category={category} (id={category_id}) hours={hours} ...")
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
    print(f"  OK {category}@{hours}h: {len(raw)} raw trends")
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


def parse_volume(volume) -> int:
    if volume is None:
        return 0
    if isinstance(volume, (int, float)):
        return int(volume)
    s = str(volume).strip().lower()
    digits = "".join(ch for ch in s if ch.isdigit())
    n = int(digits) if digits else 0
    if "m" in s and n < 1000000:
        n *= 1000000
    elif "k" in s and n < 1000:
        n *= 1000
    return n


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

        seen.add(q_lower)
        cleaned.append({
            "query": query,
            "search_volume": parse_volume(item.get("search_volume", 0)),
            "increase": increase,
            "categories": cats,
            "news_token": item.get("news_page_token") or item.get("news_token"),
        })

    cleaned.sort(key=lambda x: (x["increase"], x["search_volume"]), reverse=True)
    return cleaned


def keyword_match(query: str, keywords: list) -> bool:
    q = f" {query.lower()} "
    for kw in keywords:
        k = kw.lower().strip()
        if not k:
            continue
        # Space-padded short tokens like "ai " / " app" avoid false positives
        if k.endswith(" ") or k.startswith(" "):
            if k in q or k.strip() in query.lower().split():
                return True
        elif k in query.lower():
            return True
    return False


def merge_unique(base: list, extra: list) -> list:
    seen = {t["query"].lower() for t in base}
    out = list(base)
    for t in extra:
        key = t["query"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    out.sort(key=lambda x: (x["increase"], x["search_volume"]), reverse=True)
    return out


def build_one_source(api_key: str, source: dict, all_pool_raw=None) -> dict:
    print(f"\n{'=' * 50}")
    print(f"Building source: {source['id']} -> {source['output']}")
    print(f"{'=' * 50}")

    hours_list = source.get("hours") or [24]
    all_raw = []
    for cat in source["categories"]:
        for hours in hours_list:
            try:
                all_raw.extend(fetch_category(api_key, cat, hours))
            except Exception as e:
                print(f"  !! Skip category {cat}@{hours}h: {e}")

    cleaned = clean_trends(all_raw, source.get("blacklist_extra", []))

    # Scoop tech/finance-ish queries from the general "all" pool when the niche is thin
    if source.get("scoop_from_all") and source.get("keyword_include") and all_pool_raw is not None:
        scooped = clean_trends(all_pool_raw, source.get("blacklist_extra", []))
        scooped = [t for t in scooped if keyword_match(t["query"], source["keyword_include"])]
        before = len(cleaned)
        cleaned = merge_unique(cleaned, scooped)
        print(f"  + Scoop from all via keywords: +{len(cleaned) - before} (now {len(cleaned)})")

    top_n = int(source.get("top_n", 80))
    top_trends = cleaned[:top_n]

    output_data = {
        "matrix_metadata": {
            "source_id": source["id"],
            "categories": source["categories"],
            "hours": hours_list,
            "strategy": "Category + lookback + optional keyword scoop via SerpAPI",
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

    # Prefetch general "all" once if any niche wants to scoop keywords from it
    all_pool_raw = None
    needs_all = any(s.get("scoop_from_all") for s in targets)
    if needs_all:
        try:
            # Prefer 24h active pool; also pull 7-day for more candidates
            all_pool_raw = []
            all_pool_raw.extend(fetch_category(api_key, "all", 24))
            all_pool_raw.extend(fetch_category(api_key, "all", 168))
        except Exception as e:
            print(f"  !! Could not prefetch all pool for scoop: {e}")
            all_pool_raw = []

    for source in targets:
        build_one_source(api_key, source, all_pool_raw=all_pool_raw)

    print("\nAll requested trend files updated.")


if __name__ == "__main__":
    main()
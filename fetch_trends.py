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

# Slim sources: ~4 SerpAPI searches per full run (all@24 prefetch reused).
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
        "reuse_all_pool": True,
    },
    {
        "id": "finance",
        "output": "trends_finance.json",
        "categories": ["business_and_finance"],
        "hours": [24],
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
        # One tech window only; also daily-only (outside cron is 4x/day for other niches).
        "min_hours_between_fetches": 20,
        "categories": ["technology"],
        "hours": [24],
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
        "categories": ["entertainment"],
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


def existing_seed_count(path: str) -> int:
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        seeds = data.get("trending_seeds") or []
        return len(seeds) if isinstance(seeds, list) else 0
    except Exception:
        return 0



def hours_since_update(path: str):
    """Hours since matrix_metadata.config.last_updated_hkt (naive local), or None."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stamp = (
            ((data.get("matrix_metadata") or {}).get("config") or {}).get("last_updated_hkt")
            or ""
        ).strip()
        if not stamp:
            return None
        then = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - then).total_seconds() / 3600.0
    except Exception:
        return None


def should_fetch_source(source: dict, force_ids: set) -> bool:
    """Tech is daily-only; other sources run every outside dispatch."""
    sid = source.get("id") or ""
    if sid in force_ids:
        return True
    max_age = source.get("min_hours_between_fetches")
    if not max_age:
        return True
    age = hours_since_update(source["output"])
    if age is None:
        print(f"  -> {sid}: no prior stamp — will fetch")
        return True
    if age >= float(max_age):
        print(f"  -> {sid}: last update {age:.1f}h ago (>= {max_age}h) — will fetch")
        return True
    print(f"  -> {sid}: skipped (last update {age:.1f}h ago; daily-only, need >= {max_age}h)")
    return False

def write_output(path: str, output_data: dict) -> bool:
    seeds = output_data.get("trending_seeds") or []
    prev = existing_seed_count(path)
    if len(seeds) == 0 and prev > 0:
        print(f"  !! Keep existing {path} ({prev} seeds) — refusing to overwrite with empty")
        return False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path} -> {len(seeds)} seeds")
    return True


def build_one_source(api_key: str, source: dict, all_pool_raw=None) -> int:
    print(f"\n{'=' * 50}")
    print(f"Building source: {source['id']} -> {source['output']}")
    print(f"{'=' * 50}")

    hours_list = source.get("hours") or [24]
    all_raw = []
    fetch_errors = 0

    if source.get("reuse_all_pool") and all_pool_raw is not None:
        print("  -> Reusing prefetched all@24 pool (no extra SerpAPI call)")
        all_raw.extend(all_pool_raw)
    else:
        for cat in source["categories"]:
            for hours in hours_list:
                try:
                    all_raw.extend(fetch_category(api_key, cat, hours))
                except Exception as e:
                    fetch_errors += 1
                    print(f"  !! Skip category {cat}@{hours}h: {e}")

    cleaned = clean_trends(all_raw, source.get("blacklist_extra", []))

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
            "strategy": "Slim SerpAPI: few categories + scoop from all@24; empty never overwrites",
            "provider": "serpapi",
            "config": {
                "keywords_count": len(top_trends),
                "fetch_errors": fetch_errors,
                "last_updated_hkt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        },
        "trending_seeds": top_trends,
    }

    written = write_output(source["output"], output_data)
    if top_trends[:5]:
        print("   Sample:", ", ".join(t["query"] for t in top_trends[:5]))
    return len(top_trends) if written else existing_seed_count(source["output"])


def main():
    parser = argparse.ArgumentParser(description="Fetch categorized Google Trends via SerpAPI")
    parser.add_argument(
        "--id",
        default=None,
        help="Only build one source id, e.g. finance / tech / entertainment / general",
    )
    parser.add_argument(
        "--force-tech",
        action="store_true",
        help="Fetch tech even if updated within min_hours_between_fetches",
    )
    args = parser.parse_args()

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("[FATAL] SERPAPI_API_KEY is missing.")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Trends Hub starting (SerpAPI, slim)...")

    targets = SOURCES
    if args.id:
        targets = [s for s in SOURCES if s["id"] == args.id]
        if not targets:
            raise SystemExit(f"Unknown source id: {args.id}")

    all_pool_raw = []
    needs_all = any(s.get("scoop_from_all") or s.get("reuse_all_pool") for s in targets)
    if needs_all:
        try:
            all_pool_raw.extend(fetch_category(api_key, "all", 24))
        except Exception as e:
            print(f"  !! Could not prefetch all pool for scoop: {e}")
            all_pool_raw = []

    force_ids = set()
    if args.force_tech or os.getenv("FORCE_TECH", "").strip() in ("1", "true", "yes"):
        force_ids.add("tech")

    seed_counts = []
    for source in targets:
        if not should_fetch_source(source, force_ids):
            seed_counts.append(existing_seed_count(source["output"]))
            continue
        seed_counts.append(build_one_source(api_key, source, all_pool_raw=all_pool_raw))

    total = sum(seed_counts)
    print(f"\nDone. Seed counts per source: {seed_counts} (total={total})")
    if total == 0:
        print("[FATAL] All sources empty — likely SerpAPI quota/error. Not wiping prior JSON.")
        raise SystemExit(2)

    print("All requested trend files updated (empty overwrites skipped).")


if __name__ == "__main__":
    main()

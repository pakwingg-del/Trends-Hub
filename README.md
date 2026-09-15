# Trends Hub

US Google Trends feeder for `content-factory` sites.

## Provider

Uses **SerpAPI** (`engine=google_trends_trending_now`) with `SERPAPI_API_KEY`.

Outputs keep the existing `trending_seeds` shape so `generator.py` does not need changes.

| File | Niche |
|------|--------|
| `master_trends.json` | general |
| `trends_finance.json` | business / shopping |
| `trends_tech.json` | technology |
| `trends_entertainment.json` | entertainment / beauty |

Point each site `config.json` `trends_url` at the matching raw GitHub JSON URL.

## Setup

1. Add GitHub Actions secret `SERPAPI_API_KEY` (from https://serpapi.com/).
2. Remove old `SEARCHAPI_API_KEY` if present.
3. Run workflow **Fetch US Trends** manually once (`workflow_dispatch`), or wait for the schedule (3x daily).

## Local run

```bash
export SERPAPI_API_KEY=your_key
pip install requests
python fetch_trends.py
# or one niche:
python fetch_trends.py --id finance
```

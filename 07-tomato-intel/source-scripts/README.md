# Source scripts: architecture notes

The production scrapers live in a private repository and are not included here. This document describes what each one does at a high level.

The platform pulls from a fleet of platform-specific scrapers, all writing to a single Supabase warehouse table. Each scraper is a small Node.js or Python module orchestrated by APScheduler inside a Docker container. No credentials, no environment variables, no API endpoints are reproduced in this public folder.

## Scraper inventory

| Scraper | Source | Cadence | Records emitted |
|---|---|---|---|
| LinkedIn posts | Apify actor for public LinkedIn search | Every 6 hours | Posts matching configured keywords, plus author + reactions |
| LinkedIn jobs | Apify actor | Daily | Job postings matching role + region filters |
| Google news | Custom Python (FastAPI scheduler) | Every 4 hours | Article URL, title, summary, language |
| Twitter / X mentions | Apify actor | Daily | Posts + author profile snapshot |
| Reddit threads | PRAW-based Python module | Every 8 hours | Posts + comment trees from configured subreddits |
| Trustpilot reviews | Apify actor | Daily | Reviews for tracked competitors + own brand |
| Jobindex (Danish job board) | Apify actor | Daily | Job postings, employer-side metadata |
| Facebook group monitor | Apify actor | Daily | Posts + reactions from configured public groups |
| Meta Ads Library | Apify actor | Daily | Active ads, advertiser, impressions estimate |
| Price feeds | Custom Python adapter | Hourly | Crop prices, exchange-rate snapshots |
| Regulatory portals | trafilatura + Playwright | Daily | Regulation summaries by country |

## Common pattern

Every scraper follows the same shape:

1. Read configuration from a versioned YAML (sources, keywords, regions, cadence)
2. Call the platform's API or run a headless-browser actor with explicit timeouts
3. Normalise the response into a typed record matching the warehouse schema
4. Upsert into Supabase, idempotent on a content hash
5. Write a heartbeat row to a `scrape_runs` table so the Scrape Status panel can show health

If a source goes silent for more than its configured grace period, the dashboard surfaces it as a warning before the team notices a content gap.

## Why this folder doesn't contain the code

The scrapers were built against specific client agreements and contain integration details (API keys, content selectors against fragile DOM structures, account credentials) that don't belong in a public repo. The architecture above is reproducible from the description without needing the source.

For the reproducible signal-scoring layer that runs on top of the scraped data, see [`../python/signal_scoring.py`](../python/signal_scoring.py).

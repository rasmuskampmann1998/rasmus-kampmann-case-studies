# Market Intelligence Platform (Tomato Intel)

> *Real-time competitive and market intelligence for an agricultural technology client. Hundreds of sources, hundreds of articles interpreted daily, surfaced as a continuously updated dashboard with semantic search and agentic scraping.*

## Live demo

The platform is deployed at **[tomato-intel-api.onrender.com](https://tomato-intel-api.onrender.com)**. Open it to see the live dashboard, weekly briefings, and the Scrape Status panel.

## The question

The client team needed continuous visibility across a fragmented intelligence landscape. Crop prices, regulatory changes across 27 countries, competitor product launches, patent filings, news in three languages, social-media signals. Manual monitoring was a full-time job that produced incomplete, stale briefings.

The brief: build a platform that collects, processes, and interprets this information automatically, then surfaces only what's relevant.

## What I built

A full-stack market intelligence platform. The capabilities it demonstrates:

- **Agentic scraping.** A Claude-driven agent decides which source to pull from next, plans the scrape sequence, and reroutes when a source fails. The agent has tools for triggering an Apify actor, parsing custom HTML, hitting a JSON API, and writing back to the warehouse. It picks the right tool for the source on its own.
- **Web scraping at scale.** Around 800 sources across LinkedIn, Twitter, Reddit, Google News, Jobindex, Meta Ads Library, Trustpilot, price feeds, and regulatory portals. Mix of Apify actors and custom Python (trafilatura, Playwright, selectolax).
- **Python automation.** Every scraper is a small Python or Node.js module, idempotent on a content hash, with explicit retry-and-backoff. No manual triggers.
- **ETL pipeline.** Raw scrape rows land in a Supabase staging table, then a typed transform step writes them into the canonical intelligence schema with consistent country codes, source IDs, and timestamps.
- **SQL warehouse with migrations.** PostgreSQL on Supabase, schema versioned with timestamped migration files (`migrations/0001_initial.sql` through `0008_company_hub.sql`). Every schema change is reviewable in the repo.
- **Cron jobs.** APScheduler runs inside the FastAPI process. Different jobs on different cadences: hourly for price feeds, every 4 hours for news, daily for jobs and social, weekly for the briefing PDF.
- **REST API.** FastAPI exposes endpoints for the dashboard, weekly briefings, source-health, and a chat endpoint that wraps an LLM with retrieval.
- **LLM interpretation layer.** Each incoming article gets read by Claude, classified by topic and region, summarised in plain language, and scored for relevance against the client's strategic priorities. Cheaper Haiku-tier models do bulk classification. Sonnet-tier models handle the harder cross-source reconciliation.
- **RAG with semantic search.** All interpreted articles are embedded into a `pgvector` table on Supabase. The dashboard's chat panel lets the user ask "what's been happening with seed prices in Spain this month?" and the answer is composed from the top-k retrieved articles. The model cites its sources inline.
- **Multi-LLM routing.** Different prompts route to different model families. Claude for the heavy reasoning, lighter models for translation and bulk summarisation. A single routing layer handles fallbacks if a provider rate-limits.
- **Live demo and PDF export.** React frontend deployed on the same Render service as the API. Weekly PDF export bundles the top stories of the week and ships to leadership on Monday morning.

## Data flow

```
Agentic scraper (Claude + tool-use)
    │
    ▼
Raw scrape table (Supabase staging)
    │
    ▼
Transform + dedupe (Python ETL)
    │
    ▼
Canonical intelligence schema (PostgreSQL)
    │
    ├──► Claude classification + summarisation (LLM)
    │       │
    │       ▼
    │   Structured intelligence + embeddings (pgvector)
    │
    ▼
FastAPI endpoints
    │
    ├──► React dashboard (live)
    ├──► Chat panel (RAG + semantic search)
    ├──► Weekly PDF (auto-generated)
    └──► Email alerts (on high-priority signals)
```

Every step is observable. A Scrape Status panel inside the dashboard shows source health, last successful run, and row counts. Sources that go silent are flagged before they become a blind spot.

## How agentic scraping works

Traditional scrapers are scripted. They run a fixed sequence and break when a source changes layout.

The agentic scraper takes a goal ("get the latest seed-price news for Spain") and decides itself which source to query, how to parse it, and what to do if a source fails. The agent has a small toolset:

- `apify_actor.run(actor_id, input)` runs a pre-built Apify scraper
- `http_get(url)` fetches a URL with sensible defaults
- `parse_article(html)` extracts the main article body using trafilatura
- `store(record)` writes a typed row to the warehouse
- `mark_source_failed(source_id, reason)` flags the source as needing manual attention

The model plans the sequence, executes it through tool calls, and routes around failures. The pattern uses Claude's tool-use API directly with structured JSON tool definitions.

## Schema migrations

Eight versioned migration files live in `migrations/`. Each one is a single forward-only PostgreSQL script. Examples of what they cover:

- `0001_initial.sql` core tables: sources, raw_scrapes, articles
- `0002_embeddings.sql` adds `pgvector` extension and the embedding column
- `0003_scrape_runs.sql` introduces the per-run logging used by the Scrape Status panel
- `0005_translations.sql` adds a translation table for multi-language articles
- `0007_chat_history.sql` persists user chat threads for the RAG panel
- `0008_company_hub.sql` adds a company-aggregation layer that joins articles to tracked competitors

Migrations are applied via a small Python harness that records the latest applied version in a `schema_migrations` table.

## What it surfaces

A typical week's dashboard pulls out things like:

- A regulatory change in one EU country that's about to apply bloc-wide.
- A competitor launching a product in a specific region, picked up from a local trade-press article plus a job posting on their careers page.
- A price movement that breaks a recent trend, with the article that caused it linked underneath.
- A semantic-search query like "patent activity around drought-tolerant tomato varieties" returning a ranked list of articles and patents with one-paragraph summaries.

The job that used to take a person most of a week now takes the system a few hours of compute and surfaces more than the manual version did.

## Tech

- **Backend:** FastAPI, Docker
- **Database:** Supabase (PostgreSQL with `pgvector` for embeddings), versioned SQL migrations
- **Scheduling:** APScheduler
- **Scraping:** Apify actors + custom Python (trafilatura, Playwright, selectolax)
- **Agentic layer:** Claude API with tool-use, MCP-style tool definitions
- **AI:** Claude (Haiku and Sonnet, routed by task), multi-LLM fallback
- **Embeddings + RAG:** OpenAI text-embedding for vectorisation, retrieval via `pgvector`
- **Frontend:** React, served from the same Render service as the API
- **Observability:** Sentry, structured logging, Scrape Status panel

## What's in this folder

- `python/signal_scoring.py` reproducible scoring layer that runs on top of scraped signal data
- `source-scripts/` architecture-only README describing each scraper at a high level
- `powerbi/dashboard-spec.md` Power BI page spec for clients who prefer it over React
- `sql/schema.sql` simplified canonical schema
- `slides/deck-spec.md` executive-summary slide blueprint

## Note on the public version

The production scrapers contain integration details (API keys, content selectors, account credentials) that don't belong in a public repo. The architecture is described above. The signal-scoring layer in `python/` is a reproducible generic version that works on a synthetic dataset.

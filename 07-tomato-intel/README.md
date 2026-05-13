# Market Intelligence Platform (Tomato Intel)

> *Real-time competitive and market intelligence for an agricultural technology client. 218 sources, hundreds of articles a day, surfaced as a continuously updated dashboard with semantic search, agentic scraping, multi-LLM interpretation, and a RAG chat panel.*

## Live demo

Deployed at **[tomato-intel-api.onrender.com](https://tomato-intel-api.onrender.com)**. Open the dashboard, click a category, ask the chat panel a question, watch a scraper run on demand. Everything visible is the live production build.

## The question

Agriculture commercial teams work across regulatory shifts, competitor moves, price signals, and patent activity. The information exists. It just lives in 200+ disconnected sources, in three languages, and nobody has time to read them all. Manual monitoring at this scope is structurally broken. Every commercial team in this space is making decisions on stale signals.

This client was no exception. The client team needed continuous visibility across a fragmented intelligence picture. Crop prices, regulatory changes across 27 countries, competitor product launches, patent filings, news in three languages, social signals. Manual monitoring was a full-time job that produced incomplete, stale briefings.

The brief: build a platform that collects, processes, and interprets this information automatically, then surfaces only what's relevant.

## What I built

A full-stack intelligence platform with four pillars:

- **Agentic scraping.** A Claude-driven agent decides which source to pull from next, plans the scrape sequence, and reroutes when a source fails. Two agentic surfaces total: the scraper agent and a streaming ScraperBuilder that proposes new source configs from a URL.
- **Multi-LLM interpretation.** Every article gets read, classified, translated if needed, summarised, scored for relevance, and embedded. Claude Haiku for bulk, Claude Sonnet for synthesis, DeepSeek for non-English perspectives, Perplexity for real-time web search.
- **RAG dashboard with citations.** The chat panel composes answers from the top-k retrieved articles using pgvector cosine similarity. Sources cite inline as clickable pills, Perplexity-style.
- **Observability and ops.** Per-source run logging, health endpoints, rate limiting, Sentry, PostHog, and a "Run now" button on every source.

Current state: 218 active sources across 10 categories, 191 healthy, 21 empty, 0 failing. 13 external services wired together. One Render box, $7/month.

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
    ├──► Claude interpretation (Haiku, batched)
    │       │
    │       ▼
    │   Interpreted items + Voyage embeddings (pgvector)
    │
    ▼
FastAPI endpoints
    │
    ├──► React dashboard (live)
    ├──► Chat panel (RAG + multi-LLM judge)
    ├──► REST API v1 (bearer tokens)
    ├──► Weekly PDF (auto-generated)
    └──► CLI (intel ask, intel news, intel report)
```

Every step is observable. A Scrape Status panel inside the dashboard shows source health, last successful run, items found, and a 10-run history per source. Sources that go silent get flagged before they become a blind spot.

## The 7-layer scraper chain

A cost-sorted fallback chain. Free layers run first. Money only spent when free layers fail.

| Layer | Method | Cost |
|---|---|---|
| 1 | RSS / Atom feed parser (`feedparser`) | Free |
| 2 | Raw HTML fetch (`httpx`) | Free |
| 3 | BeautifulSoup4 extraction | Free |
| 3.5 | Crawl4AI headless Chromium | Free |
| 4 | Playwright browser automation | Free |
| 5 | Jina Reader API | Free tier |
| 6 | Firecrawl anti-bot scraper | 100 req/month free |
| 7 | Apify (last resort) | $35 / 3 months budget |

Sources marked `is_required=true` unlock a final fallback to Apify, and after that to Claude as a one-off rescue. The rest of the catalogue stops at free layers. Apify runs before Claude in the rescue chain. Free first, money second, model third.

## How agentic scraping works

Traditional scrapers are scripted. They run a fixed sequence and break when a source changes layout.

The agentic scraper takes a goal ("get the latest seed-price news for Spain") and decides itself which source to query, how to parse it, and what to do if a source fails. The agent has a small toolset:

- `apify_actor.run(actor_id, input)` runs a pre-built Apify scraper
- `http_get(url)` fetches a URL with sensible defaults
- `parse_article(html)` extracts the main article body using trafilatura
- `store(record)` writes a typed row to the warehouse
- `mark_source_failed(source_id, reason)` flags the source as needing manual attention

The model plans the sequence, executes it through tool calls, and routes around failures. The pattern uses Claude's tool-use API directly with structured JSON tool definitions.

The second agentic surface is the ScraperBuilder. It takes a URL from the user, proposes a scraper config (method, selectors, category, language), tests it live, and offers a one-click "add to sources" button. Server-Sent Events stream the agent's thinking into the UI panel step-by-step.

## RAG with citations

The chat panel is where the agentic and retrieval layers meet.

Embeddings live in `company_products.embedding` as `vector(1024)`. A PostgreSQL RPC called `match_company_products` does cosine similarity search via pgvector. The agent's `query_company_context` tool pulls the user's company profile, runs a semantic product search, and pre-pends both to the system prompt before generating the answer.

Citations are rendered Perplexity-style: `[1]`, `[2]`, `[3]` as highlighted superscript pills inside the response, each clickable to the source URL.

Three chat modes:

| Mode | Model | Behaviour |
|---|---|---|
| Standard | Claude Haiku | Single-LLM, fast |
| DeepSeek | DeepSeek-V3 | Chinese-language perspective |
| Deep | Claude Sonnet (judge) | Parallel fan-out + synthesis |

## Multi-LLM ensemble with a judge

`parallel_research()` fans out the same question to DeepSeek and Perplexity asynchronously. DeepSeek brings non-English source coverage. Perplexity brings real-time web search. Both return raw answers with their own citations.

Claude Sonnet then receives both raw answers plus the original question, and synthesises a single response that reconciles them. It flags disagreements, drops hallucinations one model committed but the other didn't, and merges citations.

The judge pattern beats single-LLM for cross-source questions because the synthesis step has visibility into where models disagree. A single LLM has no reference point.

## Schema as code

Four versioned migrations cover the evolution of the warehouse. Every change is reviewable in the repo:

| Migration | Date | What it adds |
|---|---|---|
| `20260507000001_source_metadata.sql` | May 2026 | Country, tier, priority, slug columns on sources |
| `20260507000002_new_categories.sql` | May 2026 | dna, robotics, ai_tech categories |
| `20260508000001_company_context.sql` | May 2026 | `company_context` + `company_products` (pgvector 1024d) + `match_company_products` RPC |
| `20260509000001_api_tokens.sql` | May 2026 | SHA256-hashed bearer tokens for REST API |

Main tables (14 total) group by purpose:

- **Content:** `scraped_items`, `interpreted_items`, `translation_cache`
- **Users:** `search_profiles`, `profile_items`, `company_context`, `company_products`, `demo_profiles`
- **System:** `api_tokens`, `webhook_subscriptions`, `social_watched_accounts`
- **Observability:** `scrape_runs`, `competitor_activity`, `trend_alerts`, plus the `source_health` view

Row-level security is on. The demo profile system loads its system prompt from `demo_profiles` so non-engineers can change agent behaviour by editing a database row.

## Scheduling and source quality

APScheduler runs inside the FastAPI process. Different jobs on different cadences:

- Hourly: price feeds
- Every 90 minutes: interpreter (translation + summary + embedding)
- Daily 06:00 UTC: news, competitors, crops, regulations + interpreter + trend detector
- Weekly Monday 07:00 UTC: genetics, patents
- Every 3 days: 6-platform social scraper + competitor intel classifier
- Weekly Monday 07:30 UTC: PDF digest via SendGrid

Source quality controls that turn a demo into a system:

- **Junk-title filter.** `is_junk_title()` drops nav widgets, image alt-text, and auction entries before they hit the warehouse.
- **News diversity cap.** Page-0 query pulls 4× page size and round-robins by source with a cap of 3 per source per page.
- **UTF-8 hardening.** `config/sources.json` is opened with explicit `encoding='utf-8'`. The Windows default cp1252 was corrupting em-dashes into mojibake.
- **Language relabel.** 47 items from one source were tagged English but contained Cyrillic. Re-tagged as Ukrainian. The frontend hides items with non-Latin titles that claim to be English.

About 470 historic junk rows were purged in a single cleanup pass.

## Observability

Every scrape run writes a row to `scrape_runs`: source id, status, items found, duration, error message. ~240 rows a day at current cadence.

The Scrape Status panel renders that table with All / Mine / Failing filters, per-source 10-run history, last successful run timestamp, and a "Run now" button per source.

Backend has `/health` for the Render health probe, Sentry for error tracking, slowapi for rate limiting (chat 30/min, reports 5/min, search 60/min). Frontend has PostHog for product analytics. Every external dependency is no-op without its API key, so the system runs locally without paid services.

## REST API and CLI

Eight v1 endpoints exposed via FastAPI:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/news` | GET | Paginated interpreted items |
| `/api/v1/competitors` | GET | Competitor activity feed |
| `/api/v1/query` | POST | Chat agent query (non-streaming) |
| `/api/v1/report` | POST | Generate market report |
| `/api/v1/products` | POST | Bulk push company products |
| `/api/v1/feedback` | POST | Submit item feedback |
| `/api/v1/tokens` | POST | Create API token |
| `/api/v1/tokens/bootstrap` | POST | One-time bootstrap (disabled after use) |

Bearer tokens are SHA256-hashed in the `api_tokens` table. The CLI lives at `tools/cli/intel.py`:

```
intel ask "What are competitors doing in hybrid tomatoes?"
intel news --category genetics --limit 20
intel competitors --company "Syngenta"
intel report --topic "resistance traits Q3"
intel products push products.json
```

## Deployment

One Render web service. Frankfurt region. Starter plan, $7/month. The service serves both FastAPI and the React SPA from the same origin, which eliminates CORS entirely.

Build command:

```bash
pip install -r requirements.txt
playwright install chromium
cd frontend && npm install && npm run build
```

Render serves `frontend/dist` as static files with SPA history-mode fallback after all API routers. `VITE_API_BASE=""` so every fetch in the React app is same-origin relative. No second host, no second secret store, no CORS surface to defend.

I pivoted to this from a Vercel + Render split mid-build. The split kept failing committer-checks and forced env-var sync across two services. Single host wiped the whole class of problems.

## What it surfaces

A typical week's dashboard pulls things like:

- A regulatory change in one EU country that's about to apply bloc-wide
- A competitor launching a product in a region, picked up from a local trade-press article plus a job posting on their careers page
- A price movement that breaks a recent trend, with the article that caused it linked underneath
- A semantic-search query like "patent activity around drought-tolerant tomato varieties" returning a ranked list of articles and patents with one-paragraph summaries

The job that used to take a person most of a week now takes the system a few hours of compute and surfaces more than the manual version did.

## Numbers

218 active sources. 191 healthy. 21 empty. 0 failing. ~470 junk rows purged. 11 mojibake source names repaired. 47 items relabeled. 13 external services. $35 Apify budget per 3 months. $7 hosting bill per month. One person built it.

## What I'd do differently

About 21 sources are permanently blocked. China gov, Hainan, mcx.gov.ru, AgWeb, Sainsbury Lab. Cloudflare or geo-IP gated. Even with the full 7-layer chain plus Apify plus Claude rescue, none of them open up. Cracking them needs paid residential proxies with CN and RU IPs. I chose not to spend that money for this build. If I rebuilt, I'd budget for it from day one.

I removed Voyage embeddings from the keyword search path partway through. Semantic search was costing more than it returned for the keyword-heavy queries users actually ran. The embeddings stay in the schema for the RAG chat (where they earn their keep) but the `/search/smart` endpoint runs as a PostgREST keyword `ilike` now.

IEEE Spectrum returns valid tech headlines but they're general tech, not agriculture. I never built the keyword filter at scrape time. It's a 30-minute fix I should have done before shipping.

## Tech

- **Backend:** FastAPI, Docker
- **Database:** Supabase (PostgreSQL with `pgvector` for embeddings), versioned SQL migrations
- **Scheduling:** APScheduler
- **Scraping:** Apify actors + custom Python (trafilatura, Playwright, selectolax, feedparser)
- **Agentic layer:** Claude API with tool-use, two agentic surfaces (scraper + ScraperBuilder)
- **AI:** Claude (Haiku and Sonnet, routed by task), DeepSeek-V3, Perplexity, multi-LLM judge synthesis
- **Embeddings + RAG:** Voyage AI `voyage-4-lite` for vectorisation (1024-dim), retrieval via `pgvector`
- **Frontend:** React 18 + Vite + Tailwind, served same-origin from FastAPI
- **Hosting:** Render, single web service, Frankfurt region
- **Observability:** Sentry, PostHog, structured logging, Scrape Status panel
- **Other:** SendGrid for weekly PDF digest

## What's in this folder

- `python/signal_scoring.py` reproducible scoring layer that runs on top of scraped signal data
- `source-scripts/` architecture-only README describing each scraper at a high level
- `powerbi/dashboard-spec.md` Power BI page spec for clients who prefer it over React
- `slides/deck-spec.md` executive-summary slide blueprint

## Note on the public version

The production scrapers contain integration details (API keys, content selectors, account credentials) that don't belong in a public repo. The architecture is described above. The signal-scoring layer in `python/` is a reproducible generic version that works on a synthetic dataset.

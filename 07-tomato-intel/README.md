# Market Intelligence Platform (Tomato Intel)

> *Real-time competitive and market intelligence for an agricultural technology client. 228 sources, hundreds of articles a day, surfaced as a continuously updated dashboard with agentic scraping, multi-LLM interpretation, a RAG chat panel, and a cross-source signal-detection layer that flags when one entity surfaces across patents, funding, and regulation in the same window.*

## Live demo

Deployed at **[tomato-intel-api.onrender.com](https://tomato-intel-api.onrender.com)**. Open the dashboard, click a category, ask the chat panel a question, watch a scraper run on demand. Everything visible is the live production build.

## The question

Agriculture commercial teams work across regulatory shifts, competitor moves, price signals, and patent activity. The information exists. It just lives in 200+ disconnected sources, in three languages, and nobody has time to read them all. Manual monitoring at this scope is structurally broken. Every commercial team in this space is making decisions on stale signals.

This client was no exception. The client team needed continuous visibility across a fragmented intelligence picture. Crop prices, regulatory changes across 27 countries, competitor product launches, patent filings, news in three languages, social signals. Manual monitoring was a full-time job that produced incomplete, stale briefings.

The brief: build a platform that collects, processes, and interprets this information automatically, then surfaces only what's relevant.

## What I built

A full-stack intelligence platform with five pillars:

- **Agentic scraping.** A Claude-driven agent decides which source to pull from next, plans the scrape sequence, and reroutes when a source fails. Two agentic surfaces total: the scraper agent and a streaming ScraperBuilder that proposes new source configs from a URL.
- **Multi-LLM interpretation.** Every article gets read, classified, translated if needed, summarised, scored for relevance, and embedded. Claude Haiku for bulk, Claude Sonnet for synthesis, DeepSeek for non-English perspectives, Perplexity for real-time web search.
- **RAG dashboard with citations.** The chat panel composes answers from the top-k retrieved articles using pgvector cosine similarity. Sources cite inline as clickable pills, Perplexity-style.
- **Signal detection.** Articles get reduced to named entities, then a deterministic rule engine flags cross-source patterns — the same entity appearing across ≥3 unrelated sources, or across patents + funding + regulation in one window. Signals rank against each customer's watchlist so the dashboard shows the few that matter, each cited back to verbatim source quotes.
- **Observability and ops.** Per-source run logging, health endpoints, rate limiting, Sentry, PostHog, and a "Run now" button on every source.

Current state: 228 active sources across 10 categories. 13 external services wired together. One Render box, $7/month. The interpretation and RAG layers are production-proven; the signal-detection layer is built and runs end-to-end, with signal richness growing as more history accumulates (cross-source convergence is rare until an entity recurs over time).

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
    │       │
    │       ▼
    │   Signal pipeline: dedupe → entity extract (Haiku) → resolve →
    │   5-rule detector → watchlist-ranked signals (cited to evidence)
    │
    ▼
FastAPI endpoints
    │
    ├──► React dashboard (live, incl. Signals view)
    ├──► Chat panel (RAG + multi-LLM judge)
    ├──► Signals API (/signals: feed, entity context, NL search, state, report)
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

## From articles to signals

Interpretation answers "what does this article say." Signal detection answers a harder question: "what is happening across all the articles that no single one of them states." A competitor filing a patent is a data point. That same competitor filing a patent, closing a funding round, and appearing in a regulatory notice in the same week is a *move* — and no individual source reports it as one.

The pipeline that produces signals runs after interpretation:

```
interpreted items
   → dedupe          (title-similarity clustering; collapse the same story
                       reported by many outlets into one cluster)
   → entity extract  (Claude Haiku reads each cluster, pulls named entities:
                       company, person, geography, disease, regulation,
                       variety, technology, commodity, event — generic terms
                       like "tomato" or "agriculture" are rejected)
   → resolve         (rapidfuzz folds aliases — "Rijk Zwaan" / "Rijk Zwaan
                       B.V." / "RZ" — into one canonical entity)
   → detect          (a deterministic, LLM-free rule engine over the
                       entity-to-source graph)
   → rank            (score each signal against the customer's watchlist;
                       surface the top few, suppress the rest)
```

The detector is five rules. It is intentionally **not** an LLM — every rule is a SQL aggregation or a numeric comparison, so a signal is auditable and reproducible, never a model's opinion:

| Rule | Fires when | Status |
|---|---|---|
| Convergence | One entity appears in ≥3 unrelated sources across ≥2 STEEP buckets (e.g. patent + funding + regulation) within 7 days | Live |
| Weak signal | One entity in ≥3 unrelated sources, single bucket | Live |
| Anomaly | An entity's mention count this week is >2σ above its 30-day baseline | Self-suppresses until 30 days of history exist |
| First-mover | An entity appears in a niche/specialist source ≥14 days before mainstream pickup | Needs source-tier labelling |
| Geographic spread | A story cascades CN-press → EU-press → US-press over weeks | Needs cross-region coverage |

Rules that lack their data precondition suppress themselves and log why, rather than firing noise. Every signal that does fire carries `signal_evidence` rows — verbatim quotes from the source articles it was built from. That is the "no hallucination" guarantee by construction: a signal cannot claim something no source said, because the claim is one click from the quote.

The honest limit: cross-source convergence only fires when the *same specific entity* recurs across sources, which is rare in any single week at this source volume. The mechanism is built and verified end-to-end; signal density grows as history accumulates and alias-folding tightens. The earlier temptation — extracting generic terms so "signals" fire constantly — produces noise, not intelligence, and the entity extractor explicitly rejects it.

## The signals dashboard

A dedicated Signals view sits alongside the category feeds. Each signal renders as a card:

- **Type + STEEP bucket + urgency**, and a confidence shown as a Strong / Medium / Weak chip — never a raw decimal, because the rule weights are not calibrated probabilities and shouldn't be dressed up as one.
- **Evidence on demand** — open any card to read the verbatim source quotes it was built from, each linking out to the original article.
- **Entity drill-in** — click an entity chip to see its 30-day mention timeline, the other signals it appears in, and its geographic spread.
- **Natural-language search** — ask "competitor activity in hybrid tomatoes" and a Haiku pass maps it to a structured filter over the signal store.
- **Triage** — approve, promote, or reject a signal; the state persists per customer and feeds back into ranking.
- **On-demand reports** — generate an executive brief from the current signals, with a post-generation citation check that refuses to ship a report referencing a signal that doesn't resolve.

The whole layer is scoped per customer through a thin overlay (`customer_accounts`, watchlists, taxonomies, per-signal state) over a shared signal store — so two customers see different rankings of the same underlying detection, without duplicating the data.

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
- **Signals:** `entities` (conformed dimension) + `entity_candidates` (pipeline staging), `signals`, `signal_evidence`, `signal_entity_links`, and the customer overlay (`customer_accounts`, `customer_watchlists`, `customer_taxonomies`, `customer_signal_state`), surfaced through a fan-out-safe `v_signals_with_entities_and_evidence` view

A later set of migrations adds the intelligence layer (lookup tables instead of enums so a new entity kind is an INSERT not a schema change; the entity/signal/customer tables above; anon-read grants). Row-level security is on. The demo profile system loads its system prompt from `demo_profiles` so non-engineers can change agent behaviour by editing a database row.

## Scheduling and source quality

APScheduler runs inside the FastAPI process. Different jobs on different cadences:

- Hourly: price feeds
- Every 90 minutes: interpreter (translation + summary + embedding)
- Daily 06:00 UTC: news, competitors, crops, regulations + interpreter + trend detector
- Weekly Monday 07:00 UTC: genetics, patents
- Every 3 days: 6-platform social scraper + competitor intel classifier
- Weekly Monday 07:30 UTC: PDF digest via SendGrid
- Weekly Monday 10:00 UTC: the intelligence pipeline (dedupe → entity extract → resolve → detect → rank), guarded by a weekly LLM-spend ceiling and a zero-signal alert that flags a broken run rather than silently producing nothing

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

228 active sources across 10 categories. ~470 junk rows purged. 11 mojibake source names repaired. 47 items relabeled. 13 external services. Five-rule signal detector over a conformed entity graph. $35 Apify budget per 3 months. $7 hosting bill per month. One person built it.

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

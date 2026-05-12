# Slide Deck Spec: Market Intelligence Platform

McKinsey one-rule format. One problem, one finding (action title), one recommendation per slide.

## Slide 1: Cover

**Title:** A continuously updated market intelligence platform for an agricultural-technology business.
**Subtitle:** Hundreds of sources, agentic scraping, semantic search, and weekly auto-generated briefings.

## Slide 2: Executive summary (SCR)

- **Situation:** The team needed continuous visibility across crop prices, regulations in 27 countries, competitor moves, patents, and social signals.
- **Complication:** Manual monitoring was a full-time job that still produced incomplete, stale briefings.
- **Resolution:** A platform that scrapes around 800 sources, interprets every article through an LLM layer, and surfaces only the relevant items in a live dashboard plus a weekly PDF.

## Slide 3: Finding 1

**Action title:** *Agentic scraping handles source layout changes that break scripted scrapers.*
- Chart: side-by-side stability comparison (scripted vs agent-driven) over the last 90 days.
- Therefore: Migrate the highest-churn sources to the agentic path. Keep the cheap scripted scrapers for stable platforms.

## Slide 4: Finding 2

**Action title:** *Multi-LLM routing keeps interpretation costs predictable while preserving quality on the hard cases.*
- Chart: per-article cost breakdown by model tier, with average quality score per tier.
- Therefore: Default to the cheap tier for bulk classification. Escalate to the higher tier on cross-source reconciliation.

## Slide 5: Finding 3

**Action title:** *Semantic search over interpreted articles gives the team a question-answering surface that raw scraping never did.*
- Chart: example query plus the top-3 retrieved results with citations.
- Therefore: Promote the chat panel from "exploratory feature" to a primary entry point on the dashboard.

## Slide 6: Finding 4

**Action title:** *The weekly auto-generated PDF replaces the manual Monday briefing entirely.*
- Chart: time-saved comparison (hours per week, before vs after).
- Therefore: The team can deprecate the manual briefing cadence and reallocate that capacity to acting on what the briefing surfaces.

## Slide 7: Operational health

**Action title:** *The Scrape Status panel surfaces source outages before any content goes missing.*
- Chart: dashboard screenshot with the panel highlighted.
- Therefore: Make the panel part of the daily ops check-in for whoever is on call.

## Slide 8: Next steps

1. Expand source coverage to two more regulatory portals.
2. Add an auto-translation layer for sources in additional languages.
3. Ship an alert API so other systems can subscribe to high-priority signals.
4. Quarterly review of the relevance-scoring prompts to keep them aligned with shifting strategic priorities.

## Note on the public version

The production scrapers are not included in the public repo. The interpretation layer and signal-scoring code are reproducible on a synthetic dataset.

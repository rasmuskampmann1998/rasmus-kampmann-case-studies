# Power BI — Channel Performance Dashboard

A four-page Power BI dashboard built on the star schema in `../data/`. It loads ten CSVs, exposes 20 DAX measures, and answers one question: across acquisition channels, which produces the most won revenue fastest **and keeps the customers it wins** — and where is sales-dialer time being spent that doesn't return?

A working PBIP project that implements this spec sits alongside it (`ChannelPerformance.pbip`). It was authored and validated with **pbi-cli** (`pbi report validate` returns `valid: True`, 31 files). This file is the human-readable spec. The `.pbip` is the build. The measure list below is copied verbatim from `ChannelPerformance.Dataset/definition/tables/_Measures.tmdl`, so spec and model do not drift.

> **Phase 8 (2026-05-18):** added a post-won churn / retention axis. `fact_deals` carries four new columns (`churn_date_key`, `is_churned`, `retained_months`, `churned_mrr`); five retention measures were added; the "Efficiency & Dialer ROI" page became "Channel Economics" (the dialer cut was non-zero for only 2 of 10 channels, so most of its visuals were structurally empty); the "Trend & Loss" page became "Retention & Loss" (the monthly win-rate trend plotted noise, `created_date` is uniform-random in the generator, so there is no designed time trend). "Best channel" now means wins fast, low cost, and the wins stay.

> **Phase 9 (2026-05-18):** restyle. A custom theme JSON (`channel-performance-theme.json`, applied headless via `pbi report set-theme`) gives the report one calm palette with red reserved for the dialer / kill channels so colour carries the narrative. Chart grammar simplified: every comparison chart is a horizontal **bar**, the two former `column` visuals on Channel Overview were converted; **cards** for single KPIs and **matrices** for tables are kept; exactly one **line** chart was added (the retention-depth curve below). No pie, scatter, donut, or treemap anywhere by rule. Visual count: 25 across 4 pages (8 / 6 / 3 / 8), `pbi report validate` → `valid: True`, 32 files.

## Chart grammar (the rule)

One grammar, applied everywhere:

- **Card** — a single headline number (KPI tiles).
- **Bar** — any comparison across a categorical dimension (channel, group, employee band, lost reason). Horizontal, so long channel names read without rotation.
- **Line** — only where the x-axis is a genuinely ordered domain. The report has exactly one: won customers by `retained_months` (1 to 12). A line is never used for a categorical axis or a fabricated time trend.
- **Matrix** — a small table where the cell values matter (channel × metric).

No pie, donut, scatter, treemap, gauge, or funnel. If a chart cannot be a bar, a line on an ordered axis, a card, or a matrix, the question is wrong, not the chart type.

Every number quoted here is recomputed by `../python/verify_numbers.py`. That script is the source of truth.

## Data model

Star schema: three fact tables joined to seven conformed dimensions. `dim_channel` is the primary analytical dimension. All relationships are single-direction (dim to fact), one-to-many.

```
   dim_rep ─┐                       ┌─ dim_company
            ├─ fact_touches ────────┤
  dim_date ─┘                       └─ dim_channel

   dim_rep ──┐                            ┌─ dim_company
   dim_stage ┼─ fact_deals ───────────────┤ dim_channel ─ dim_campaign
   dim_date ─┘  (created/won/lost keys)   └─ dim_lost_reason

   dim_rep ─┐                       ┌─ dim_company
            ├─ fact_meetings ───────┤
  dim_date ─┘  (meeting_date_key)   └─ dim_channel, deal_key → fact_deals
```

**Tables to load** (from `../data/`):
- `dim_date.csv` — date_key (key), date (typed `dateTime`), year, quarter, month, month_name (sorted by month), week_of_year, day_of_week, is_business_day. Marked as the date table statically via `__PBI_MarkAsDateTable`.
- `dim_channel.csv` — channel_key (key), channel_name, channel_group, is_dialer_motion, cost_model
- `dim_campaign.csv` — campaign_key (key), campaign_name, channel_key, segment, launch_date
- `dim_company.csv` — company_key (key), company_name, industry, employee_band, revenue_band_usd, region, company_form, company_age_band
- `dim_rep.csv` — rep_key (key), rep_name, rep_team, tenure_band
- `dim_stage.csv` — stage_key (key), stage_name, stage_order, funnel_step
- `dim_lost_reason.csv` — lost_reason_key (key), lost_reason, reason_category
- `fact_touches.csv` — touch_key (key), company_key, channel_key, rep_key, touch_date_key → dim_date[date_key], touch_dialer_minutes
- `fact_deals.csv` — deal_key (key), channel_key, company_key, campaign_key, rep_key, stage_key, lost_reason_key, created/won/lost/**churn**_date_key → dim_date[date_key] (active = created_date_key; won/lost/churn inactive, use USERELATIONSHIP for timing), mrr_usd, dialer_hours_attributed, **is_churned, retained_months, churned_mrr** (post-won, only meaningful when is_won = 1)
- `fact_meetings.csv` — meeting_key (key), deal_key → fact_deals[deal_key], company_key, channel_key, rep_key, meeting_date_key → dim_date[date_key]; `days_to_close` / `days_from_first_touch` typed `double`

## DAX measures

All 20 measures follow the repo's `[Domain] · [Metric]` naming convention. Verbatim from `_Measures.tmdl`:

```DAX
Channel · Deals = COUNTROWS ( fact_deals )

Channel · Won Deals = SUM ( fact_deals[is_won] )

Channel · Lost Deals = SUM ( fact_deals[is_lost] )

Channel · Win Rate = DIVIDE ( [Channel · Won Deals], [Channel · Deals] )

Channel · Volume Share =
DIVIDE ( [Channel · Deals], CALCULATE ( [Channel · Deals], REMOVEFILTERS ( dim_channel ) ) )

Channel · Meetings Held =
CALCULATE ( COUNTROWS ( fact_meetings ), fact_meetings[meeting_status] = "Held" )

Channel · Meeting Cancel Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_meetings ), fact_meetings[meeting_status] = "Cancelled" ),
    COUNTROWS ( fact_meetings )
)

Revenue · Won MRR USD = CALCULATE ( SUM ( fact_deals[mrr_usd] ), fact_deals[is_won] = 1 )

Revenue · Avg MRR per Won Deal = DIVIDE ( [Revenue · Won MRR USD], [Channel · Won Deals] )

Revenue · Won MRR Share =
DIVIDE ( [Revenue · Won MRR USD], CALCULATE ( [Revenue · Won MRR USD], REMOVEFILTERS ( dim_channel ) ) )

Channel · Dialer Hours = SUM ( fact_deals[dialer_hours_attributed] )

-- THE HEADLINE METRIC. Blank for non-dialer channels by design.
Channel · MRR per Dialer Hour = DIVIDE ( [Revenue · Won MRR USD], [Channel · Dialer Hours] )

Channel · Avg Days to Won =
CALCULATE ( AVERAGE ( fact_deals[deal_age_days] ), fact_deals[is_won] = 1 )

Channel · Cancellation Share of Losses =
DIVIDE (
    CALCULATE ( [Channel · Lost Deals], dim_lost_reason[lost_reason] = "Meeting No-Show / Cancelled" ),
    [Channel · Lost Deals]
)

Channel · Re-booking Trap Flag =
IF ( SELECTEDVALUE ( dim_channel[channel_name] ) = "Re-bookings", 1, 0 )

-- Phase 8: post-won churn / retention. is_churned / churned_mrr are columns
-- on fact_deals, so these sum over the ACTIVE fact_deals→dim_channel
-- relationship with a plain CALCULATE filter — no RELATED, no inactive-
-- relationship traversal (that class of bug is uncatchable by pbi validate
-- and the offline MCP; the safe construction is encoded by design).
Channel · Churned Deals = CALCULATE ( SUM ( fact_deals[is_churned] ), fact_deals[is_won] = 1 )

Channel · Retention Rate =
VAR Won = [Channel · Won Deals]
RETURN IF ( Won > 0, 1 - DIVIDE ( [Channel · Churned Deals], Won ) )

Revenue · Churned MRR = CALCULATE ( SUM ( fact_deals[churned_mrr] ), fact_deals[is_won] = 1 )

Revenue · Net Revenue Retention =
DIVIDE ( [Revenue · Won MRR USD] - [Revenue · Churned MRR], [Revenue · Won MRR USD] )

Channel · Won & Retained = [Channel · Won Deals] - [Channel · Churned Deals]
```

**Retention reads directionally on small-n channels.** Re-bookings has ~14 won deals, Instagram ~19, SEO ~30. Their realised retention is noisy — the trap verdict stands on the robust win-rate axis (Re-bookings n=312); retention corroborates on a second axis and is hedged in every place it appears.

## Dashboard pages

The implemented report has 25 visuals across 4 pages (8 / 6 / 3 / 8), `pbi report validate` → `valid: True`, 32 files. By type: 10 bar, 11 card, 3 matrix, 1 line. No column / pie / scatter / donut / treemap.

### Page 1 — Channel Overview

The 30-second view: which channel wins, which earns, which fills the pipe.

- **KPI cards (5):** `Channel · Deals` (7,300), `Channel · Won Deals` (1,585), `Channel · Win Rate` (21.7% blended), `Revenue · Won MRR USD` ($1,235,395), `Revenue · Avg MRR per Won Deal` ($779)
- **Bar:** `Channel · Win Rate` by `dim_channel[channel_name]`. Cold Calling sits at 8.6% on 60% of volume. Referral, Cross-sell, LinkedIn all clear 60%.
- **Bar (Pareto):** `Revenue · Won MRR USD` by `dim_channel[channel_name]` (Phase 9: was a column chart; converted to bar with the rest of the report)
- **Bar:** `Channel · Deals` by `dim_channel[channel_name]` — the volume picture, dominated by Cold Calling

### Page 2 — Channel Economics

The "which channel wins **and keeps** what it wins" story. This page carries the recommendation. (Phase 8: replaced "Efficiency & Dialer ROI" — the dialer cut had a value for only 2 of 10 channels, so a dialer-led page was structurally empty for the other 8. Dialer ROI is still here, demoted to a corner card pair: it is a real finding but not the efficiency axis for non-dialer channels.)

- **Bar (headline):** `Revenue · Net Revenue Retention` by `dim_channel[channel_name]`. Warm channels hold 80–95% of won MRR through the M12 window; Cold Calling keeps ~50%. The post-sale half of the dilution trap.
- **Bar:** `Channel · Retention Rate` by `dim_channel[channel_name]`. Logo retention — same shape, customers not dollars. Small-n channels (Re-bookings, Instagram, SEO) read directionally.
- **Matrix:** `Channel · Win Rate` by `dim_channel[channel_name]` rows — the all-channel economics table; add Retention / NRR / Net MRR as value columns Desktop-side.
- **Matrix:** `Revenue · Net Revenue Retention` by `dim_channel[channel_group]` rows
- **Card:** `Channel · MRR per Dialer Hour` — filter to a dialer channel; Cold Calling $19/hr, Re-bookings $5/hr. The scarce resource sits on the worst-retaining channels.
- **Card:** `Channel · Avg Days to Won` — expansion closes in under a week; Cold Calling and Re-bookings 3–4× slower.

### Page 3 — Channel × ICP

Does firmographic fit change the channel ranking? It does not. Channel is the dominant axis.

- **Matrix:** `Channel · Win Rate` by `dim_channel[channel_name]` rows. The employee-band columns are added Desktop-side (the offline matrix bind supports rows plus values only — see the runbook).
- **Bar:** `Channel · Win Rate` by `dim_company[employee_band]` — the 6-20 band is mildly better (23.7% vs 21.0%), a tilt, not a driver
- **Bar:** `Channel · Win Rate` by `dim_company[industry]` — Consulting / Marketing / Transport close near zero regardless of channel

### Page 4 — Retention & Loss

The "do the wins stay, and what kills the deals we lose" story. (Phase 8 replaced "Trend & Loss"; the noise trend line was removed. Phase 9 added back a line, but an honest one: its x-axis is `retained_months`, a real ordered 1-to-12 domain, not a fabricated calendar trend.)

- **Line (lead):** `Channel · Won & Retained` by `fact_deals[retained_months]` (1 to 12), legend `dim_channel[channel_group]`. Won customers plotted by how many months they stayed before churning. Expansion holds its line high across all twelve months; Outbound drops away early. This is the one line chart in the report and the only place a line is honest, because months-retained is a genuinely ordered axis.
- **Bar:** `Channel · Won & Retained` by `dim_channel[channel_name]` — the wins that actually stayed, the count the best-channel verdict turns on
- **Bar:** `Revenue · Churned MRR` by `dim_channel[channel_name]` — where won revenue leaks back out; Cold Calling is the largest churned-MRR bar
- **Bar (Pareto base):** `Channel · Lost Deals` by `dim_lost_reason[reason_category]` — No-response dominates at ~43%
- **Card:** `Channel · Retention Rate` (74.2% blended)
- **Card:** `Revenue · Net Revenue Retention` (74.0% blended)
- **Card:** `Channel · Meeting Cancel Rate`
- **Card:** `Channel · MRR per Dialer Hour` — filter to Re-bookings to read the trap ($5/hr)

## Conditional formatting (apply Desktop-side)

- Win Rate cells: red below 10%, amber 10–40%, green above 40%
- MRR per dialer hour: red below $50, amber $50–$200, green above $200
- Time to won: green at or under 14 days, amber 15–30, red above 30

Colour is load-bearing in this theme (red marks the worst channels). For a real client delivery that has to meet accessibility requirements, the red/amber/green scale would need a pattern or shape fallback, or an accessible-palette variant, because the navy/green/red midtones are hard to separate under deuteranopia and collapse in greyscale print. This is a synthetic method demo, so the limitation is stated rather than engineered around.

## Import notes

- `dim_date` is marked as the date table statically (`annotation __PBI_MarkAsDateTable = {"dt":"date"}`), so no Desktop `mark-date` step is needed.
- For `fact_deals`, the active relationship is `created_date_key`. `won_date_key`, `lost_date_key`, and `churn_date_key` are inactive; use `USERELATIONSHIP` for won/lost/churn timing. The five churn measures deliberately do **not** traverse these — they filter `is_churned` / `churned_mrr` (columns on `fact_deals`) over the active channel relationship, so no `RELATED`-across-inactive semantic error is possible (the class of bug that bit the sibling NorthStarFunnel model and that `pbi validate` cannot catch).
- `fact_meetings[deal_key]` → `fact_deals[deal_key]` is inactive; activate with `USERELATIONSHIP` for any meeting-to-deal cycle measure.
- Hide all `*_key` columns. Surface only dimension attributes.
- All measures live on the `_Measures` table (no data) so they sort to the top.
- `Channel · MRR per Dialer Hour` is blank for non-dialer channels. Keep it that way. The contrast between a blank cell and Cold Calling's $19 is the entire argument.
- **Theme:** `channel-performance-theme.json` is applied by `_gen_report.py` via `pbi report set-theme`. The palette reserves red (`#B5482F`) for the worst channels; `good`/`neutral`/`bad` map green/amber/red so the Desktop-side conditional formatting above lands on the same scale. Re-running `_gen_report.py` re-applies it; do not restyle visuals by hand in Desktop.
- **Power BI Desktop strips the churn measures on save.** Opening `ChannelPerformance.pbip` in Desktop and saving rewrites `_Measures.tmdl` from the loaded model and drops the five Phase-8 churn measures (replacing them with an empty `measure Measure` stub). Observed twice. `_gen_report.py` now refuses to build if the dataset has fewer than 20 measures or any churn measure is missing — re-assert the Phase-8 churn block in `_Measures.tmdl` before rebuilding. Never hand-edit measures in Desktop for this project; edit the TMDL and regenerate.

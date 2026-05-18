# Power BI — Full Funnel Dashboard (Case Study #12)

A four-page Power BI dashboard built on the star schema in `../data/`. Loads nine CSVs, exposes 17 DAX measures, and surfaces the analytical narrative end-to-end: top-of-funnel volume, the firmographic ICP (employee band + industry), rep variance, and lost-reason mix.

A working PBIP project that implements this spec lives alongside it (`NorthStarFunnel.pbip`). It was authored and validated with **pbi-cli** (`pbi report validate` → `valid: True`, 28 files). This file is the human-readable spec; the `.pbip` is the build. The measure list below is copied verbatim from `NorthStarFunnel.Dataset/definition/tables/_Measures.tmdl` — spec and model do not drift.

## Data model

Star schema: three fact tables joined to six conformed dimensions (dim_campaign was removed — it was unconnected and unused). All relationships single-direction (dim → fact), 1-to-many.

```
   dim_rep ─┐                ┌─ dim_company
            ├─ fact_calls ───┤
  dim_date ─┘                └─ (call_date_key → dim_date)

   dim_rep ─┐                ┌─ dim_company
            ├─ fact_meetings ┤
  dim_date ─┘                └─ (meeting_date_key → dim_date, deal_key → fact_deals)

   dim_rep ─┐                            ┌─ dim_company ─ dim_source
            ├─ fact_deals ───────────────┤
  dim_date ─┘   (created/won/lost keys)  └─ dim_stage ─ dim_lost_reason
```

**Tables to load** (from `../data/`):
- `dim_date.csv` — date_key (key), date (typed `dateTime`), year, quarter, month, month_name, week_of_year, day_of_week, is_business_day
- `dim_company.csv` — company_key (key), company_name, industry, employee_band, revenue_band_usd, region, accounting_system, company_type, company_age_band
- `dim_rep.csv` — rep_key (key), rep_name, rep_team, tenure_band
- `dim_stage.csv` — stage_key (key), stage_name, stage_order, funnel_step
- `dim_source.csv` — source_key (key), source_name, channel
- `dim_lost_reason.csv` — lost_reason_key (key), lost_reason, reason_category
- `fact_calls.csv` — call_key (key), company_key, rep_key, call_date_key → dim_date[date_key]
- `fact_meetings.csv` — meeting_key (key), deal_key → fact_deals[deal_key], company_key, rep_key, meeting_date_key → dim_date[date_key]; `days_to_close` / `days_from_create` typed `double`
- `fact_deals.csv` — deal_key (key), company_key, rep_key, source_key, stage_key, lost_reason_key, created_date_key / won_date_key / lost_date_key → dim_date[date_key] (active = created_date_key; inactive on won/lost, use USERELATIONSHIP)

## DAX measures

All 17 measures follow the repo's `[Domain] · [Metric]` naming convention. Verbatim from `_Measures.tmdl`:

```DAX
Funnel · Total Calls = COUNTROWS ( fact_calls )

Funnel · Connected Calls = SUM ( fact_calls[is_connected] )

Funnel · Connect Rate = DIVIDE ( [Funnel · Connected Calls], [Funnel · Total Calls] )

Funnel · Meetings Booked = SUM ( fact_calls[is_meeting_booked] )

Funnel · Meetings Held =
CALCULATE ( COUNTROWS ( fact_meetings ), fact_meetings[meeting_status] = "Held" )

Funnel · Meeting Show Rate = DIVIDE ( [Funnel · Meetings Held], [Funnel · Meetings Booked] )

Funnel · Won Deals = SUM ( fact_deals[is_won] )

Funnel · Lost Deals = SUM ( fact_deals[is_lost] )

Funnel · Win Rate Meeting->Won = DIVIDE ( [Funnel · Won Deals], [Funnel · Meetings Held] )

Funnel · Win Rate Call->Won = DIVIDE ( [Funnel · Won Deals], [Funnel · Total Calls] )

Funnel · Cancellation Share of Losses =
DIVIDE (
    CALCULATE ( [Funnel · Lost Deals], dim_lost_reason[lost_reason] = "Meeting No-Show / Cancelled" ),
    [Funnel · Lost Deals]
)

Revenue · MRR Won USD = CALCULATE ( SUM ( fact_deals[mrr_usd] ), fact_deals[is_won] = 1 )

Revenue · Avg MRR per Won Deal = DIVIDE ( [Revenue · MRR Won USD], [Funnel · Won Deals] )

-- Held meetings only (the old version averaged cancelled/no-show too).
Funnel · Avg Days Call->Meeting =
CALCULATE ( AVERAGE ( fact_meetings[days_from_create] ), fact_meetings[meeting_status] = "Held" )

-- Won deals only; days_to_close is now a numeric column so the ISBLANK guard
-- correctly excludes cancelled meetings (was a text column → silent coercion bug).
Funnel · Avg Days Meeting->Won =
CALCULATE (
    AVERAGE ( fact_meetings[days_to_close] ),
    FILTER (
        fact_meetings,
        RELATED ( fact_deals[is_won] ) = 1 && NOT ISBLANK ( fact_meetings[days_to_close] )
    )
)

-- Anti-ICP industries actually present in the data.
ICP · Anti-ICP Flag =
IF ( SELECTEDVALUE ( dim_company[industry] ) IN { "Consulting", "Marketing", "Transport" }, 1, 0 )

ICP · Sweet-Spot Lift vs Baseline =
VAR Baseline = [Funnel · Win Rate Meeting->Won]
VAR SweetSpot = CALCULATE ( [Funnel · Win Rate Meeting->Won], dim_company[employee_band] = "6-20" )
RETURN SweetSpot - Baseline
```

Fixed from the prior version: `CALCULATEDS`→`CALCULATE`; the won-filter on the cycle measure; the `Anti-ICP Flag` industry list; the `Avg Days Call->Meeting` held-only filter; all names to `[Domain] · [Metric]`.

## Dashboard pages

The implemented report has 21 visuals across 4 pages (pbi-cli `report info` confirms 8 / 5 / 3 / 5).

### Page 1 — Funnel Overview

The 30-second view: how much volume comes in, where it leaks, what gets won.

- **KPI cards (5):** `Funnel · Total Calls` (102,007), `Funnel · Connect Rate` (30.8%), `Funnel · Meetings Held` (2,829), `Funnel · Win Rate Meeting->Won` (12.8%), `Revenue · MRR Won USD` ($278,449)
- **Bar:** `Funnel · Won Deals` by `dim_stage[stage_name]`, sorted by `stage_order`
- **Line (won count):** `Funnel · Won Deals` by `dim_date[month]`
- **Line (revenue):** `Revenue · MRR Won USD` by `dim_date[month]` — split into a *separate* chart from won-count (the two differ ~800×; one shared Y axis was misleading)

### Page 2 — ICP & Segments

The "who converts vs. who doesn't" story. Drives the lead-scoring recommendation on slide 10.

- **Column chart (the headline):** `Funnel · Win Rate Meeting->Won` by `dim_company[employee_band]`, the 6-20 column highlighted — 37.5% sweet spot vs ~3% everywhere else
- **Bar:** `Funnel · Win Rate Meeting->Won` by `dim_company[industry]` — Consulting / Marketing / Transport ≈0%
- **Bar:** `Funnel · Win Rate Meeting->Won` by `dim_company[company_type]` — minor tilt
- **Bar (flat by design):** `Funnel · Win Rate Meeting->Won` by `dim_company[accounting_system]` — caption: "no signal — every prospect already has a system"
- **Matrix:** `Funnel · Win Rate Meeting->Won` by `dim_company[employee_band]` rows. The employee-band × industry cross-tab is a Desktop-side enhancement (the offline matrix bind supports rows + values only) — see the runbook.

### Page 3 — Rep Performance

The "rep skill is the lever inside the meeting" story.

- **Horizontal bar (sorted):** `Funnel · Win Rate Meeting->Won` by `dim_rep[rep_name]` — top ~29% vs bottom ~2.5%
- **Column:** `Funnel · Total Calls` by `dim_rep[rep_name]`
- **Table:** rep_name + `Funnel · Win Rate Meeting->Won` (extend Desktop-side with rep_team, Show Rate, MRR)

### Page 4 — Velocity & Loss

The "cancellations kill more deals than competitors" story.

- **Bar (Pareto base):** `Funnel · Lost Deals` by `dim_lost_reason[reason_category]` (No-response dominates at ~57%)
- **Column:** `Funnel · Won Deals` by `fact_meetings[days_to_close]` — meeting→won cycle histogram
- **Card:** `Funnel · Cancellation Share of Losses` (43.0%)
- **Card:** `Funnel · Avg Days Meeting->Won` (11 days)
- **Card:** `Revenue · Avg MRR per Won Deal` ($769)

## Conditional formatting (apply Desktop-side)

- Win Rate cells: red <10%, amber 10–15%, green >15%
- Cycle days: green ≤14, amber 15–30, red >30
- Heatmap: diverging scale, 0% → 40%+ (the 6-20 cell saturates)

## Import notes

- **Mark `dim_date` as the Date table** via `pbi table mark-date dim_date --date-column date` (in the Desktop runbook — `powerbi/README.md`). The auto-date internal markers are deliberately not hand-authored in the TMDL.
- For `fact_deals`, active relationship = `created_date_key`; inactive on `won_date_key`/`lost_date_key`, use `USERELATIONSHIP` for won/lost timing.
- `fact_meetings[deal_key]` → `fact_deals[deal_key]` carries won/lost context into the cycle measures.
- Hide all `*_key` columns; surface only dim attributes.
- All measures live on the `_Measures` table (no data) so they sort to the top.
- `accounting_system` is intentionally flat / no-signal — keep it on Page 2 only as the "what doesn't predict" contrast.

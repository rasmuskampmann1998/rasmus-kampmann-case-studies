# Sales, Inventory & 24-Month Production Forecasting

> *Real-time operational intelligence for a European seed producer. Sales pipeline, raw-material inventory, and 24-month production forecasting on a single source of truth.*

## The Problem

The client is a European seed and agri-tech company. They were running their commercial operations across four disconnected Excel workbooks:

- A **sales pipeline** workbook (orders, customers, delivery windows)
- A **raw-material inventory** workbook (`VOORRAADBOEK`) updated manually by warehouse staff
- A **production planning** workbook (`Lagerstyring Model`) maintained by ops leadership
- A **24-month seed forecast** workbook updated quarterly by the founders

Each file had its own conventions, its own keys, and its own definition of "stock on hand." Reconciling them for a Monday-morning ops meeting took half a day. By Tuesday afternoon the numbers were already stale.

The goal was to replace the patchwork with a single live source of truth that joins all four datasets, surfaces operational anomalies, and runs a rolling 24-month forecast. I built it on tools the team already pays for: Power BI plus a small SQL warehouse.

## Data Architecture

Four sources are joined on `seed_code` (the company's internal SKU identifier) and `period_yyyymm`:

| Source | Refresh | Key fields |
|---|---|---|
| `sales_orders` | Daily | seed_code, order_date, qty, customer_id, delivery_window |
| `inventory_log` (VOORRAADBOEK) | Daily | seed_code, lot_id, qty_on_hand, location, last_count_date |
| `production_plan` (Lagerstyring) | Weekly | seed_code, period_yyyymm, planned_qty, status |
| `forecast_24m` | Quarterly | seed_code, period_yyyymm, forecast_qty, scenario |

The four Excel files land in a SharePoint folder. A Python ETL job reads them, validates the schema, anonymises customer names, and writes typed records into a Supabase PostgreSQL warehouse. Power BI reads directly from the warehouse via the Supabase connector.

## Findings (anonymised)

- **Top-15 seed varieties** account for 71% of forecast volume but only 38% of SKUs. The remaining 62% of SKUs are long-tail. They consume disproportionate planning attention relative to revenue contribution.
- **Production lead-time vs. delivery window** mismatch on 12 of 47 active seed lines. Production is planned to finish *after* the contracted delivery window opens. Flagging this in a dashboard turned a recurring late-shipment problem into a planning-cycle fix.
- **Inventory cover** (months of stock at current sell-through) ranges from 0.8 months on the fastest-moving seeds to 38 months on slow-movers. A simple "cover band" view lets ops triage which seeds to scale up vs. which to pause.
- **Seasonal cycle** in raw-material inflows: 64% of intake lands in Aug to Oct (post-harvest). The dashboard's "intake cliff" view made the team's quarterly cash-flow review possible in 15 minutes instead of two hours.
- **Forecast accuracy** (last 6 months, MAPE) is around 22%. Usable for ops planning, but it flagged the need for a propensity-style model in a future phase.

## Power BI Dashboard

Four pages:

1. **Sales pulse.** Orders YTD, by region, by seed variety. Top-customer concentration.
2. **Inventory cover.** Months-of-stock by seed, with a red/amber/green band based on forecast sell-through.
3. **Production schedule.** Gantt-style view of planned production windows vs. contracted delivery windows. The mismatch flag from above lives here.
4. **24-month forecast.** Rolling volume forecast by scenario (base / upside / downside), with month-on-month delta vs. the prior quarter's plan.

DAX measures are in [powerbi/dashboard-spec.md](powerbi/dashboard-spec.md).

## Tech

- **ETL:** Python (pandas, openpyxl), GitHub Actions for daily refresh
- **Warehouse:** Supabase (PostgreSQL)
- **BI:** Power BI Desktop + Power BI Service for sharing
- **Anonymisation:** `anonymize.py` (CVR / customer names to `Customer_NNNNN`)

## What's in this folder

- `data/`: anonymised CSV samples for each of the four source files
- `sql/`: schema + the analytical queries that back each dashboard page
- `python/`: `etl.py` (Excel to Supabase) and `analysis.py` (the five charts in this README)
- `powerbi/`: dashboard spec + DAX measures
- `slides/`: `deck-spec.md` (executive summary)
- `source-scripts/`: references to the original production ETL (paths only; proprietary code stays in the client repo)

## A note on the client

This is a real engagement with a real European seed company. All customer identifiers, seed codes, and exact revenue numbers in the public files are anonymised. The structural findings and the dashboard architecture are accurate.

# Invoice & Financial Dashboard

> *Live financial reporting on invoices, payments, AR ageing, and gross margin per seed variety. Built in Power BI on top of a Supabase warehouse, refreshed twice daily.*

## The Problem

Same client as the [operations case study](../10-veginova-operations/), different question. Finance had two recurring frustrations:

1. **Invoice status was opaque.** The accounting system showed what had been invoiced, but matching invoices to the order book, to actual payments received, and to the production cost of each line was a manual cross-reference in Excel.
2. **Gross margin per seed variety was unknown.** Selling price per kg varied by customer contract. Production cost per kg varied by yield and batch. Without joining the two, the company couldn't tell which seeds were genuinely profitable and which were break-even at best.

A request that started as *"can we see overdue invoices in one place?"* turned into a full financial-control dashboard. AR ageing, cash collection forecast, margin by seed, and customer profitability, all on the same Supabase plus Power BI stack already running for operations.

## Data Architecture

Three new sources are added to the existing warehouse:

| Source | Refresh | Key fields |
|---|---|---|
| `invoices` | Daily | invoice_no, customer_id, order_id, issue_date, due_date, amount_eur, status |
| `payments` | Daily | payment_id, invoice_no, payment_date, amount_eur, method |
| `production_cost` | Weekly | seed_code, period_yyyymm, cost_per_kg, yield_factor |

These join to the existing operations schema on `customer_id`, `order_id`, and `seed_code`.

## Findings (anonymised)

- **AR ageing is concentrated.** 67% of overdue invoices (by value) come from just 6 customers. Surfacing that in a sortable table changed how finance prioritises collection calls.
- **Gross margin range is wider than the team expected.** Across 47 seed varieties, gross margin per kg ranges from 8% (a contract-priced commodity seed) to 61% (a niche variety with a single distributor). Six varieties run at less than 15% margin. I flagged them for contract renegotiation.
- **Days-sales-outstanding (DSO)** sits at 47 days vs. a 30-day contract default. Two specific distributors account for most of the lag. Collection cadence was updated accordingly.
- **Cash-collection forecast** projects 14 days ahead using historical payment behaviour per customer. The forecast carried a ±9% error band over the first 90 days of use. Good enough to drive a weekly cash conversation with the founder.
- **Customer profitability ranking** revealed that the top 3 customers by *revenue* are #5, #8, and #12 by *gross profit*. A margin mix issue, not a volume issue. Sales conversations updated accordingly.

## Power BI Dashboard

Four pages, designed for finance and leadership:

1. **AR ageing.** Overdue invoices by bucket (0-30 / 31-60 / 61-90 / 90+), top-10 customers by overdue value, drill-through to invoice detail.
2. **Cash collection forecast.** 14-day rolling forecast, by customer, with confidence interval. Variance vs. last week.
3. **Gross margin by seed.** Margin per kg, by variety, sortable. Red flag for any seed below 15%.
4. **Customer profitability.** Revenue vs. gross profit rank, with the gap highlighted. Top-customer concentration on both axes.

DAX measures in [powerbi/dashboard-spec.md](powerbi/dashboard-spec.md).

## Tech

- **ETL:** Python (pandas), connects to the accounting system's CSV exports and the operations warehouse
- **Warehouse:** Supabase (PostgreSQL). Same instance as operations.
- **BI:** Power BI Desktop + Service, refresh twice daily
- **Forecasting:** Customer-level payment-behaviour model (simple exponential smoothing per customer, blended into a 14-day cash forecast)

## What's in this folder

- `data/`: anonymised sample CSVs for invoices, payments, production cost
- `sql/`: schema + the analytical queries powering each dashboard page
- `python/`: ETL, payment-forecast model, and the chart-generating analysis script
- `powerbi/`: dashboard spec + DAX measures
- `slides/`: `deck-spec.md` (executive summary)
- `source-scripts/`: pointers to the original production ETL

## A note on the client

All customer identifiers, invoice numbers, seed codes, and absolute amounts in the public files are anonymised. Structural findings, margin ranges, and the dashboard architecture are accurate.

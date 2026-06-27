# Invoices & Finance. Power BI Dashboard Spec

Power BI renders the mart and aggregates. All the work (cost attribution, the paid flag,
the reconciliation) happened upstream in the pipeline, so the measures stay thin enough
to verify by reading one line.

## Pages

### 1. Overview (P&L)
**Question:** What's the revenue, the contribution, and the cash owed, on one trusted view?

- KPI cards: revenue (basis-aware), contribution (Dækningsbidrag), outstanding (AR)
- Basis toggle slicer: Expected / Confirmed / Recognized
- Revenue by month
- The reconciliation result sits behind the revenue figure: leadership is told it ties out

### 2. Contribution by variety
**Question:** Which varieties carry the business?

- Horizontal bar: contribution margin % per variety, sorted ascending
- Filtered to real seed lines (is_seed_revenue), so licenses/logistics don't inflate it
- Conditional formatting: red on the thin-margin lines

### 3. Customer profitability
**Question:** Which customers contribute most, not just bill most?

- Scatter: revenue (x) vs contribution (y), one dot per customer
- Rank table: revenue rank beside contribution rank, with the delta highlighted
- Surfaces customers who are big on revenue but small on contribution (a mix issue)

### 4. Receivables (AR ageing)
**Question:** What's owed, how old, and what's at risk?

- Stacked bar: outstanding by ageing bucket (0-30 / 31-60 / 61-90 / 90+)
- Top customers by outstanding (the collection-priority list)
- Drill-through to invoice detail

## DAX (thin by design)

Revenue is a basis toggle, not a calculation. Contribution and outstanding are one line each.

```dax
Revenue =
SWITCH(
    SELECTEDVALUE('ref_revenue_basis'[basis], "Expected"),
    "Expected",   SUM(fct_revenue[amount_dkk_expected]),
    "Confirmed",  SUM(fct_revenue[amount_dkk_confirmed]),
    "Recognized", CALCULATE(SUM(fct_revenue[amount_dkk_expected]),
                  USERELATIONSHIP(dim_date[date_key], fct_revenue[recognition_date]))
)

COGS           = SUM(fct_revenue[cost_dkk])
Dækningsbidrag = [Revenue] - [COGS]                              -- contribution margin
Outstanding    = [Revenue (Expected)] - [Revenue (Confirmed)]   -- receivables

Seed Gross Margin % =
VAR SeedRev  = CALCULATE([Revenue], fct_revenue[is_seed_revenue] = TRUE)
VAR SeedCost = CALCULATE([COGS],    fct_revenue[is_seed_revenue] = TRUE)
RETURN DIVIDE(SeedRev - SeedCost, SeedRev)
```

The margin shown is **contribution**, not statutory profit: COGS is direct seed cost only,
overhead lives in the bookkeeping system by design.

## Refresh

- Invoices refreshed from the source workbook via the Python loader (truncate + insert, idempotent)
- The reconcile gate runs before the mart is trusted: if the tie to the ledger breaks, it fails
  before the number reaches a chart

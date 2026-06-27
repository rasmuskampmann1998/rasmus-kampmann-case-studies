# Invoice & Financial Dashboard

> *One trusted view of profit per product, profit per customer, and the cash owed, built from invoices and reconciled to the accounts within 1.25%. A planning system's financial sibling: logic in SQL, Power BI renders only.*

**The reconciliation figures are real** (the 2024 revenue match, the 1.25% tolerance). **The commercial detail is illustrative** (per-product margins, customer profitability, receivables amounts): the shape and scale of the real findings, with the confidential client figures replaced.

## The problem

Like many small businesses, the company's numbers lived in two places that didn't agree. The official accounts were structured for tax, which hid the real commercial picture: which products actually made money, which customers were worth keeping, and how much cash was tied up in unpaid invoices. The accounts said one thing, the invoices said another, and nobody could trust a single number.

## What I built

One decision shaped everything: **the invoices are the truth.** They're the record of what was actually sold, to whom, at what price. The tax accounts became a cross-check, not the source. From there: pull every invoice to line-item grain, reconcile invoice revenue against the official accounts, compute contribution margin per variety and profit per customer, and track accounts receivable.

The principle behind it: the logic lives in Postgres and SQL, and Power BI renders only. That's what lets the numbers reconcile and stay trustworthy, every figure on screen traces back to a reconciled row in the database.

## The data model

A star schema with `fct_revenue` at **invoice-line grain**. Four dimensions hang off it (`dim_date`, `dim_customer`, `dim_product`, `dim_bucket`), plus a disconnected `ref_revenue_basis` table that drives a revenue-basis toggle (Expected / Confirmed / Recognized). Keeping attributes on the dimensions means every measure can cut by product, customer, or bucket without rewriting a query.

## The reconcile gate (what makes the numbers trustworthy)

Invoice revenue is tied to the official ledger figure, and only the *unexplained* remainder has to clear the tolerance:

```python
LEDGER_PRIMAER_2024    = 2312690.21   # official 2024 primær revenue (illustrative value shown)
RECONCILING_ITEMS_2024 = 28805.41     # documented EU FX / timing
UNEXPLAINED_TOL        = 0.005        # 0.5% gate on the unexplained remainder

residual    = LEDGER_PRIMAER_2024 - invoice_revenue_2024
unexplained = residual - RECONCILING_ITEMS_2024
ok = abs(unexplained) / LEDGER_PRIMAER_2024 <= UNEXPLAINED_TOL   # OK / FAIL
```

Separating explained divergence (documented FX and timing) from unexplained divergence is the difference between "roughly right" and "every krone of the gap is accounted for." On the real engagement, 2024 revenue tied to the official figure within 1.25%. If a future load breaks the tie, the gate fails before the number reaches a chart.

## The Power BI layer (thin by design)

The measures aggregate columns the pipeline already computed. Revenue is a basis toggle, not a calculation:

```dax
Revenue =
SWITCH(
    SELECTEDVALUE('ref_revenue_basis'[basis], "Expected"),
    "Expected",   SUM(fct_revenue[amount_dkk_expected]),
    "Confirmed",  SUM(fct_revenue[amount_dkk_confirmed]),
    "Recognized", CALCULATE(SUM(fct_revenue[amount_dkk_expected]),
                  USERELATIONSHIP(dim_date[date_key], fct_revenue[recognition_date]))
)
Dækningsbidrag = [Revenue] - [COGS]                              // contribution margin
Outstanding    = [Revenue (Expected)] - [Revenue (Confirmed)]   // receivables
```

The complexity (cost attribution, the paid flag, the reconciliation) happened upstream, so a reviewer can verify every measure by reading one line.

## Scope note (honest)

The dashboard measures **contribution margin** (revenue minus the direct cost of the seed), not bottom-line profit. Overhead lives in the bookkeeping system; rebuilding it here would just duplicate the official accounts. The margin shown is contribution, the number that tells you which products carry the business.

## What's in this folder

- `sql/`: the star-schema definition and the analytical queries
- `python/`: the reconcile gate, the ingestion loader, and a synthetic-data generator
- `powerbi/`: dashboard spec and the basis-toggle DAX
- `slides/`: `deck-spec.md` (executive summary)

## A note on the client

This is a real engagement. All customer identifiers, invoice numbers, and absolute commercial amounts in the public files are illustrative stand-ins. The reconciliation method and the result (tied to the official 2024 revenue within 1.25%) are accurate.

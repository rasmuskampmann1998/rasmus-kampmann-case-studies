# Finance Dashboard: Executive Deck Spec

McKinsey one-rule format. One problem, one finding (action title), one recommendation per slide.

## Slide 1: Cover

**Title:** AR ageing, cash forecast, and true margin visibility.
**Subtitle:** From manual Excel cross-references to a live Power BI finance dashboard.

## Slide 2: Executive summary (SCR)

- **Situation:** Finance was cross-referencing invoices, payments, and production costs in Excel. Gross margin per seed and AR ageing were both blind spots.
- **Complication:** As the order book grew, collection lag and margin compression on long-tail seeds became material risks the company couldn't see.
- **Resolution:** A finance dashboard on the existing Supabase plus Power BI stack, refreshed twice daily, surfacing AR ageing, cash forecast, gross margin per seed, and customer profitability.

## Slide 3: Finding 1

**Action title:** *67% of overdue invoice value comes from just 6 customers.*
- Chart: top-10 overdue customers.
- Therefore: Targeted collection cadence for the 6 (escalation script plus weekly outreach) moved overdue value by 18% in the first month.

## Slide 4: Finding 2

**Action title:** *DSO sits at 47 days vs a 30-day contract default, concentrated in 2 distributors.*
- Chart: monthly DSO trend.
- Therefore: Renegotiate payment terms with the 2 distributors at the next contract review, or apply early-payment discounts.

## Slide 5: Finding 3

**Action title:** *6 of 47 seed varieties run at less than 15% gross margin.*
- Chart: gross margin per seed (sorted ascending).
- Therefore: Flag for contract renegotiation. Two are commodity seeds with thin margins. Consider pricing-band rules instead of bespoke contracts.

## Slide 6: Finding 4

**Action title:** *The top 3 customers by revenue are ranked #5, #8, and #12 by gross profit.*
- Chart: revenue rank vs gross-profit rank scatter.
- Therefore: It's a margin-mix issue, not a volume issue. Reframe sales conversations around variety mix, not total order size.

## Slide 7: Cash forecast

**Action title:** *14-day cash forecast lands within ±9% of actual. Good enough for a weekly cash conversation.*
- Chart: forecast vs actual over the first 90 days of use.
- Therefore: The founder gets a Monday-morning forecast email. Finance adjusts collection prioritisation by Thursday.

## Slide 8: Next steps

- Phase 2: customer-level payment-behaviour scoring (which invoice is most at risk of becoming overdue?).
- Phase 3: auto-drafted collection emails using Claude, with manual approval before send.
- Ongoing: monthly retainer covers dashboard evolution and ad-hoc finance analysis.

# Operations Dashboard: Executive Deck Spec

McKinsey one-rule format. One problem, one finding (action title), one recommendation per slide.

## Slide 1: Cover

**Title:** One source of truth for sales, inventory, and 24-month forecasting.
**Subtitle:** From four disconnected Excel workbooks to a live Power BI dashboard in six weeks.

## Slide 2: Executive summary (SCR)

- **Situation:** Operations were running on four disconnected Excel workbooks, with half a day spent reconciling them every Monday.
- **Complication:** As order volume grew, the manual workflow couldn't keep up. Late shipments, stale stock numbers, and forecast blind spots became routine.
- **Resolution:** A single source of truth built on Supabase plus Power BI, refreshed daily, with anomaly flags for the four highest-leverage operational risks.

## Slide 3: Finding 1

**Action title:** *71% of forecast volume sits in just 15 of 47 active seed varieties, but planning attention is spread evenly.*
- Chart: Pareto of forecast volume.
- Therefore: Restructure the weekly ops meeting around the top-15 first. Long-tail SKUs review monthly, not weekly.

## Slide 4: Finding 2

**Action title:** *12 of 47 seed lines have production finishing after the contracted delivery window opens.*
- Chart: production vs delivery mismatch.
- Therefore: Add a "production-vs-delivery" red flag to the Monday ops review and resolve mismatches at the planning cycle, not the shipping cycle.

## Slide 5: Finding 3

**Action title:** *Inventory cover ranges from 0.8 to 38 months across active seeds, but there was no view to triage.*
- Chart: cover-band distribution.
- Therefore: A simple RED/AMBER/GREEN cover-band view turns triage into a 5-minute scan instead of a 2-hour review.

## Slide 6: Finding 4

**Action title:** *64% of raw-material intake lands in Aug to Oct, and that cliff was invisible until now.*
- Chart: monthly intake area chart.
- Therefore: The intake-cliff view makes quarterly cash-flow planning a 15-minute conversation instead of a half-day reconciliation.

## Slide 7: Forecast quality

**Action title:** *Forecast MAPE is around 22% over 6 months. Usable for ops planning, but the next best lever is a propensity model on customer-level reorder behaviour.*
- Chart: forecast vs actual.
- Therefore: Phase 2 builds a customer-level reorder-propensity model, layered into the same dashboard.

## Slide 8: Next steps

- Phase 2: reorder-propensity model for the top-15 seeds.
- Phase 3: auto-generated weekly ops summary email from the dashboard, written by Claude.
- Ongoing: monthly retainer for dashboard evolution and ad-hoc analysis.

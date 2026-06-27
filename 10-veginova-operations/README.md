# Operations & Production Planning

> *A live system that tells a seed business what to produce, how much, and when. It reproduces the planner's own numbers exactly, validated against their spreadsheet. A planning system with scenario testing, not a statistical forecast.*

**The numbers in this public folder are illustrative.** The validation result (that the engine reproduces the planner's spreadsheet with zero mismatches) is real; the per-variety quantities here are synthetic stand-ins for the confidential client data. Same logic, scrambled numbers.

## The problem

Production planning ran on a spreadsheet the planner maintained by hand. The moment a sale landed or stock changed, the spreadsheet was out of date, and the production decisions built on it were based on stale numbers.

The stakes are high because of one fact: **seed production takes about a year.** If you discover you're short of a variety, it's already twelve months too late to make more. You can't react to a stockout. You have to see it coming. The planner was running the whole production, inventory, and sales triangle by hand: how much will we sell, how much do we have and how much is arriving, so how much must we produce and when do we start.

## What I built

I took the logic the planner was running by hand and built it into a live system. For every seed variety, it computes how much to produce from what's actually selling, what's in stock, and what's already on the way. It stays current (the plan updates when sales or stock change), it respects the one-year lead time (it flags which varieties are short and when production has to start), and it tests scenarios (a big sale, a capacity drop, a stock loss) before seed is committed.

The architectural decision that matters: **the planning logic is one SQL view, not DAX.** Power BI renders the marts and runs nothing of consequence. A production plan is stateful and has to recompute the instant sales or stock change; putting the engine in Postgres means it's correct the moment the data lands and can be tested on its own.

## The core equation

```sql
GREATEST(prod_safety + expected_sales - stock_on_hand - incoming, 0) AS production_need,
stock_on_hand + incoming - expected_sales                            AS ending_stock,
CASE WHEN NOT active THEN 'stopped'
     WHEN stock_on_hand + incoming - expected_sales < red_threshold THEN 'red'
     ELSE 'green' END                                                AS status
```

Produce enough to clear the safety buffer, never less than zero. Status is red when ending stock falls below the red line. A variety can be red yet need zero production, because it still covers its own expected sales: the system shows both, so a warning light is never mistaken for a production order.

## How it's validated

The "reproduces the planner's sheet" claim is enforced in code, not asserted. A gate checks the engine's output against known-good anchor varieties from the planner's spreadsheet (illustrative codes below), exact ending stock, exact status, exact production need:

```python
want = {
    "VAR-A": {"ending_stock": 943.03,  "status": "green", "production_need": 0},
    "VAR-B": {"ending_stock": 47.48,   "status": "red",   "production_need": 0},
    "VAR-C": {"ending_stock": -134.15, "status": "red",   "production_need": 134.15},
    "VAR-D": {"ending_stock": 2283.52, "status": "green", "production_need": 0},
}
```

`VAR-B` is the case that proves the model thinks correctly: red (below the safety line) but production need zero, because it still covers its sales. The gate also checks that the forecast channels sum exactly to each variety's expected sales, and that a committed plan appends a new snapshot rather than overwriting history. If any anchor moves, the build fails before the dashboard ships.

## The scenario layer

The what-if sliders are the one place computing logic lives in DAX, and they write nothing back. A disconnected parameter table feeds a single measure that re-applies a sales uplift to the base SQL identity, so the planner can pressure-test a scenario live without changing anything stored. A real commit goes back through the SQL layer.

## Honest limits

- The production buffer (`prod_safety`) is unseeded in this version, so the engine produces "just enough not to go negative" until a floor and months-of-cover are set per variety.
- A multi-year view exists and its first year is validated against the live plan, but the recursion beyond year one is built and not yet validated, because only one sales year is seeded. **This is a planning system with scenario testing, not statistical forecasting.** The business runs on named deals, not predictable trends.

## What's in this folder

- `sql/`: the production-planning schema and the `v_production_plan` view (the engine)
- `python/`: the validation gate and a synthetic-data generator
- `powerbi/`: dashboard spec and the one allowed what-if DAX measure
- `slides/`: `deck-spec.md` (executive summary)

## A note on the client

This is a real engagement with a real seed company. All variety codes and quantities in the public files are illustrative stand-ins. The architecture, the validation method, and the result (zero mismatches against the planner's sheet) are accurate.

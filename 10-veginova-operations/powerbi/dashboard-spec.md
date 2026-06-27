# Operations / Production Planning. Power BI Dashboard Spec

Power BI renders the marts. All planning logic lives in SQL (`ops.v_production_plan`).
The only computing DAX is the what-if slider, which writes nothing back.

## Pages

### 1. Overview
**Question:** What's the state of the plan right now?

- KPI cards: total to produce (KS), # varieties red, # needing production
  (the last two differ on purpose: a variety can be red yet need zero production
  if it still covers its own sales)
- Bar: production need by variety, coloured by red/green status
- Slicers: sales year

### 2. Production
**Question:** What do we make, and which varieties are at risk?

- Table: variety, expected sales, stock, incoming, ending stock, status, production need
- Bar: ending stock by variety against the safety red line
- Conditional formatting: red where ending stock < red_threshold
- Slicers: status, sales year

### 3. Need vs Plan
**Question:** How does the computed need compare to the planner's batch targets?

- Table: computed need beside the planner's per-variety target, with the lot-sizing gap
- So the difference between "just enough" and the planner's batch size is visible, not buried

### 4. What-if (scenario testing)
**Question:** What happens to the plan if sales, capacity, or stock change?

- Sliders: sales uplift %, inventory shock %, production capacity %
- The plan recomputes live as the sliders move; nothing is written back
- This is the one place computing logic lives in DAX

## DAX

The base measures are thin aggregations over the SQL view. The only computing measure
is the what-if, a disconnected `GENERATESERIES` parameter feeding a single `SUMX` that
re-applies the uplift to the engine's identity:

```dax
-- Parameter table (Power BI "New parameter" wizard):
-- Sales uplift % = GENERATESERIES(-0.2, 0.5, 0.05)

What-if production_need =
SUMX(
    'v_production_plan',
    'v_production_plan'[expected_sales] * ( 1 + SELECTEDVALUE('Sales uplift %'[Sales uplift %], 0) )
        - 'v_production_plan'[stock_on_hand] - 'v_production_plan'[incoming]
)

-- Headline cards (thin aggregations over the view):
Total To Produce = SUM('v_production_plan'[production_need])
Varieties Red    = CALCULATE(COUNTROWS('v_production_plan'), 'v_production_plan'[status] = "red")
Needing Production = CALCULATE(COUNTROWS('v_production_plan'), 'v_production_plan'[production_need] > 0)
```

Move the slider, the production need moves, and nothing is stored. A real commit goes
back through the SQL layer (`commit_production_plan`), not through DAX.

## Refresh

- Inputs (sales, stock, incoming) refreshed from the warehouse sheet via the Python loader
- Power BI dataset refresh pulls the recomputed `v_production_plan`; the engine is correct
  the moment the inputs land, because the logic is in the view, not the report

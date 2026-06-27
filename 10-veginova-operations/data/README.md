# Sample illustrative operations data

All variety codes and quantities are illustrative stand-ins for confidential client data.
The numbers are built so the planning engine reproduces the four anchor varieties the case
study cites (VAR-A..D), including the instructive VAR-B (red, yet production need zero).

Run `python ../python/generate_sample_data.py` to (re)create these deterministically.

## Files (the engine's inputs)

| File | Description |
|---|---|
| `product_params.csv` | One row per variety: the safety red line, active flag, and (unseeded) production buffer. |
| `forecast_sales.csv` | Expected sales per variety per channel; the channels sum to expected sales. |
| `stock_on_hand.csv` | Physical stock per variety, as refreshed from the warehouse sheet. |
| `incoming_production.csv` | Seed already on the way, net of waste. |

The plan itself (production need, ending stock, red/green status) is **not** in these files.
The engine (`sql/schema.sql :: v_production_plan`) derives it from these inputs, which is the
whole point: the logic lives in SQL, not in a spreadsheet of pre-computed answers.

The real client inputs live in the warehouse and planning sheet and are NOT included here.

# Source scripts

The production system lives in the client engagement's private repository. The architecture
mirrors what's in this folder:

- `operations-schema.sql`. The planning engine: `v_production_plan` (the one view that
  computes production need, ending stock, and red/green status), plus `commit_production_plan`
  (the dated-snapshot function).
- `apply_operations.py`. Applies the schema and runs the validation gate (the anchor-variety
  check, the forecast-channel reconciliation, the snapshot append test). The build fails if
  any anchor moves.
- `ingest/parse_stock.py`. Refreshes stock on hand from the warehouse sheet (locate columns by
  header text, upsert on the natural key).
- `Operations model.pbip`. Power BI project connected to the marts; renders only, plus the one
  what-if slider.

For the public reproducible version (illustrative data, same logic, runnable without a
database), see [`../python/`](../python/) and [`../sql/`](../sql/).

# Source scripts

The production finance pipeline lives in the client engagement's private repository. The
architecture mirrors what's in this folder:

- `ingest/parse_official_table.py`. Reads the reconciled invoice workbook (bucketed, FX'd,
  costed, paid-flagged) into staging, idempotently (truncate + insert), locating fields by
  header text.
- `transform/build_facts.py`. Transforms staging into `fct_revenue` at invoice-line grain,
  deriving the bucket class, the seed-revenue flag, and the confirmed-vs-expected amounts.
- `validate/reconcile_local.py`. The reconcile gate: ties 2024 invoice revenue to the official
  ledger figure and gates the unexplained remainder at 0.5%. If the tie breaks, the build fails
  before any number reaches a chart.
- `Finance model.pbip`. Power BI project connected to the mart; renders and aggregates only,
  with the basis-toggle slicer.

For the public reproducible version (illustrative data, same logic, runnable without a
database), see [`../python/`](../python/) and [`../sql/`](../sql/).

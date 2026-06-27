# Sample illustrative invoice data

All customer, invoice, and product identifiers and amounts are illustrative stand-ins for
confidential client data. The structure (contribution-margin spread, customer concentration,
AR ageing, a reconcile anchor) is what the case study describes.

Run `python ../python/generate_sample_data.py` to (re)create this deterministically.

## Files

| File | Description |
|---|---|
| `fct_revenue.csv` | The fact table at **invoice-line grain**: one row per line on one invoice, with expected/confirmed amounts, cost, product, customer, and the seed-revenue flag. |

The data is generated at invoice-line grain on purpose, because that is the real fact grain.
The reconcile gate in `../python/analysis.py` ties the 2024 invoice revenue to an illustrative
ledger anchor within tolerance, the same mechanism that made the real numbers trusted.

The real client invoices live in the source workbook and are NOT included here.

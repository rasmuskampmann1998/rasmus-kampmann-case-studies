# Sample anonymised invoice data

All identifiers are anonymised:
- Customers → `Customer_NNNNN` (matches the operations case study, so the two can be joined)
- Seed codes → `SEED_NNNN`
- Invoice numbers → `INV-NNNNN`

Amounts have been scaled by a random factor per row to avoid revealing actual
revenue. Structural patterns (DSO trend, AR ageing distribution, top-customer
concentration, margin range across seeds) are preserved.

## Files

| File | Rows (sample) | Description |
|---|---|---|
| `invoices.csv` | 800 | 12 months of invoices. Mixed paid/open/overdue. |
| `payments.csv` | ~680 | Partial and full payments. ~85% of invoices have at least one payment. |
| `production_cost.csv` | 564 | Monthly cost-per-kg and yield-factor for each of 47 seeds. |

Generate them locally with `python python/generate_sample_data.py`.

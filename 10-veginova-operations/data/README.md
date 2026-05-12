# Sample anonymised operations data

All customer IDs and seed codes are anonymised:
- Customers → `Customer_NNNNN`
- Seed varieties → `SEED_NNNN`

Real volumes have been scaled by a random factor per seed to avoid revealing
commercial info, while preserving the structural patterns used in the case study.

## Files

| File | Rows (sample) | Description |
|---|---|---|
| `sales_orders.csv` | 1,200 | One row per order. 18 months of history. |
| `inventory_log.csv` | 3,400 | Daily stock counts across 47 active seeds. |
| `production_plan.csv` | 410 | Production runs across base / upside / downside scenarios. |
| `forecast_24m.csv` | 2,256 | 24-month rolling forecast, 3 scenarios × 47 seeds × 16 periods. |

The originals live in the client's SharePoint and are NOT included here.

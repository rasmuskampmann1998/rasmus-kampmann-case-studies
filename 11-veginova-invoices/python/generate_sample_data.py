"""
Generate illustrative invoice-line data for the finance case study.

Deterministic (seed=99). Produces one CSV at invoice-line grain (fct_revenue), the
real fact grain. Amounts are synthetic stand-ins for confidential client data; the
structure (contribution-margin spread, customer concentration, AR ageing, a reconcile
anchor) is what the case study describes.

The reconcile gate in analysis.py ties the 2024 invoice revenue to an illustrative
ledger anchor within tolerance, the same mechanism that made the real numbers trusted.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(99)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

N_CUSTOMERS = 27
N_PRODUCTS = 31
CUSTOMERS = [f"CUST-{i:03d}" for i in range(1, N_CUSTOMERS + 1)]
PRODUCTS = [f"VAR-{i:03d}" for i in range(1, N_PRODUCTS + 1)]

# A few customers concentrate most of the volume (the ~1/5 -> ~3/4 pattern).
cust_weight = rng.pareto(1.1, N_CUSTOMERS) + 0.3
cust_weight /= cust_weight.sum()

# Per-product margin: most high (~90%), a handful thin (~60%).
prod_margin = rng.normal(0.90, 0.04, N_PRODUCTS).clip(0.55, 0.96)
thin = rng.choice(N_PRODUCTS, size=5, replace=False)
prod_margin[thin] = rng.uniform(0.55, 0.65, size=5)

rows = []
line_id = 0
for year, n_inv in [(2024, 220), (2025, 120)]:
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-20", freq="D")
    for _ in range(n_inv):
        cust = rng.choice(CUSTOMERS, p=cust_weight)
        d = pd.Timestamp(rng.choice(dates))
        n_lines = int(rng.integers(1, 4))
        for _ in range(n_lines):
            line_id += 1
            pidx = rng.integers(0, N_PRODUCTS)
            revenue = round(float(rng.gamma(2.0, 4000)) + 500, 2)
            cost = round(revenue * (1 - prod_margin[pidx]), 2)
            # ~85% of lines paid; the rest outstanding (drives AR ageing)
            paid = rng.random() < 0.85
            rows.append({
                "invoice_no": f"INV-{year}-{line_id:05d}",
                "line_id": line_id,
                "date_key": d.date().isoformat(),
                "recognition_date": d.date().isoformat(),
                "customer_key": cust,
                "product_key": PRODUCTS[pidx],
                "bucket_key": "Product",
                "amount_dkk_expected": revenue,
                "amount_dkk_confirmed": revenue if paid else 0.0,
                "cost_dkk": cost,
                "qty_1000": round(float(rng.uniform(0.5, 8.0)), 2),
                "is_seed_revenue": True,
                "line_type": None,
                "year": year,
            })

df = pd.DataFrame(rows)
df.to_csv(OUT / "fct_revenue.csv", index=False)
print(f"Wrote {len(df)} invoice lines to {OUT/'fct_revenue.csv'} "
      f"(2024 revenue {df.loc[df.year==2024,'amount_dkk_expected'].sum():,.0f})")

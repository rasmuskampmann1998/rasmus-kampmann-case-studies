"""
Generate anonymised sample CSVs for the A European seed producer invoices case study.

Deterministic (seed=99). Mirrors the structure of the operations sample data:
customer IDs match Customer_NNNNN, seed codes match SEED_NNNN.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(99)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

N_INVOICES = 800
N_CUSTOMERS = 60
CUSTOMERS = [f"Customer_{i:05d}" for i in range(1, N_CUSTOMERS + 1)]

# ── Invoices ───────────────────────────────────────────────────────────────
issue_dates = pd.date_range("2024-05-01", "2025-05-01", freq="D")
invoices = []
for i in range(N_INVOICES):
    customer = rng.choice(CUSTOMERS)
    # 8 customers are habitual late payers
    late_customers = CUSTOMERS[:8]
    issue = rng.choice(issue_dates)
    due = issue + pd.Timedelta(days=30)
    amount = round(float(rng.gamma(2.0, 1500)) + 200, 2)
    is_late = customer in late_customers and rng.random() < 0.55
    invoices.append({
        "invoice_no": f"INV-{20000 + i}",
        "customer_id": customer,
        "order_id": 100000 + int(rng.integers(0, 1200)),
        "issue_date": issue,
        "due_date": due,
        "amount_eur": amount,
        "status": "overdue" if is_late and issue < pd.Timestamp("2025-04-15") else "open",
        "currency": "EUR",
    })
inv_df = pd.DataFrame(invoices)
inv_df.to_csv(OUT / "invoices.csv", index=False)

# ── Payments ───────────────────────────────────────────────────────────────
payments = []
pay_id = 1
for _, row in inv_df.iterrows():
    if rng.random() < 0.85:  # 85% of invoices have at least partial payment
        # Late payers take 60–90 days; others ~25–35
        late_customers = CUSTOMERS[:8]
        if row["customer_id"] in late_customers:
            delay = int(rng.integers(60, 92))
        else:
            delay = int(rng.integers(20, 38))
        pay_date = row["issue_date"] + pd.Timedelta(days=delay)
        if pay_date > pd.Timestamp("2025-05-12"):
            continue
        payments.append({
            "payment_id": pay_id,
            "invoice_no": row["invoice_no"],
            "payment_date": pay_date,
            "amount_eur": round(row["amount_eur"] * rng.uniform(0.9, 1.0), 2),
            "method": rng.choice(["bank", "sepa", "card"], p=[0.7, 0.25, 0.05]),
        })
        pay_id += 1
pd.DataFrame(payments).to_csv(OUT / "payments.csv", index=False)

# ── Production cost ────────────────────────────────────────────────────────
seeds = [f"SEED_{i:04d}" for i in range(1, 48)]
months = pd.date_range("2024-05-01", "2025-05-01", freq="MS")
cost = []
for seed in seeds:
    base_cost = float(rng.uniform(0.8, 18.0))
    yield_factor = float(rng.uniform(0.75, 0.98))
    for m in months:
        cost.append({
            "seed_code": seed,
            "period_yyyymm": int(m.strftime("%Y%m")),
            "cost_per_kg_eur": round(base_cost * rng.uniform(0.95, 1.05), 4),
            "yield_factor": round(yield_factor * rng.uniform(0.95, 1.05), 4),
        })
pd.DataFrame(cost).to_csv(OUT / "production_cost.csv", index=False)

print(f"Wrote 3 sample CSVs to {OUT}")

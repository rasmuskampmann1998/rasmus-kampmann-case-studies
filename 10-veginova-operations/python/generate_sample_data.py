"""
Generate anonymised sample CSVs for the A European seed producer ops case study.

Runs deterministically (seed=42) so the four files reproduce identically.
Volumes are scaled randomly per seed_code so the absolute numbers can't be
reverse-engineered to real commercial data, but the structural patterns
(Pareto, cover bands, mismatch, intake cliff) are preserved.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

N_SEEDS = 47
N_CUSTOMERS = 60
SEED_CODES = [f"SEED_{i:04d}" for i in range(1, N_SEEDS + 1)]
CUSTOMERS = [f"Customer_{i:05d}" for i in range(1, N_CUSTOMERS + 1)]
REGIONS = ["NL", "DE", "FR", "ES", "DK", "IT"]
CHANNELS = ["direct", "distributor", "online"]

# Volume scalers. Pareto-distributed so a few seeds dominate
seed_volume_scale = rng.pareto(0.8, N_SEEDS) + 0.5
seed_volume_scale = seed_volume_scale / seed_volume_scale.sum() * 100  # normalise

# ── Sales orders ───────────────────────────────────────────────────────────
dates = pd.date_range("2023-11-01", "2025-05-12", freq="D")
orders = []
for _ in range(1200):
    seed_idx = rng.choice(N_SEEDS, p=seed_volume_scale / seed_volume_scale.sum())
    d = rng.choice(dates)
    delivery_open = d + pd.Timedelta(days=int(rng.integers(30, 180)))
    orders.append({
        "order_id": 100000 + len(orders),
        "order_date": d,
        "customer_id": rng.choice(CUSTOMERS),
        "seed_code": SEED_CODES[seed_idx],
        "qty": round(rng.gamma(2, seed_volume_scale[seed_idx] * 5), 2),
        "unit": "kg",
        "delivery_window_from": delivery_open,
        "delivery_window_to": delivery_open + pd.Timedelta(days=14),
        "region": rng.choice(REGIONS),
        "channel": rng.choice(CHANNELS, p=[0.55, 0.35, 0.10]),
    })
pd.DataFrame(orders).to_csv(OUT / "sales_orders.csv", index=False)

# ── Inventory log ──────────────────────────────────────────────────────────
inv = []
for d in pd.date_range("2023-09-01", "2025-05-10", freq="W"):
    for i, seed in enumerate(SEED_CODES):
        intake_factor = 1.0
        # Aug-Oct intake cliff
        if d.month in (8, 9, 10):
            intake_factor = rng.uniform(2.5, 5.0)
        inv.append({
            "seed_code": seed,
            "lot_id": f"L{rng.integers(10000, 99999)}",
            "qty_on_hand": round(seed_volume_scale[i] * 20 * intake_factor * rng.uniform(0.4, 1.2), 2),
            "unit": "kg",
            "location": rng.choice(["A1", "A2", "B1", "C1"]),
            "last_count_date": d,
        })
pd.DataFrame(inv).to_csv(OUT / "inventory_log.csv", index=False)

# ── Production plan ────────────────────────────────────────────────────────
prod = []
months = pd.date_range("2025-01-01", "2026-12-01", freq="MS")
for seed_idx, seed in enumerate(SEED_CODES):
    for m in rng.choice(months, size=int(rng.integers(2, 6)), replace=False):
        prod.append({
            "seed_code": seed,
            "period_yyyymm": int(m.strftime("%Y%m")),
            "planned_qty": round(seed_volume_scale[seed_idx] * 40 * rng.uniform(0.6, 1.4), 2),
            "status": rng.choice(["planned", "in_progress", "done", "paused"], p=[0.45, 0.20, 0.30, 0.05]),
            "scenario": "base",
        })
pd.DataFrame(prod).to_csv(OUT / "production_plan.csv", index=False)

# ── 24-month forecast ──────────────────────────────────────────────────────
fc = []
fc_months = pd.date_range("2025-05-01", "2027-04-01", freq="MS")
for seed_idx, seed in enumerate(SEED_CODES):
    for m in fc_months:
        base = seed_volume_scale[seed_idx] * 18
        for scen, mult in [("base", 1.0), ("upside", 1.25), ("downside", 0.75)]:
            fc.append({
                "seed_code": seed,
                "period_yyyymm": int(m.strftime("%Y%m")),
                "forecast_qty": round(base * mult * rng.uniform(0.85, 1.15), 2),
                "scenario": scen,
                "forecast_run": "2025-04-15",
            })
pd.DataFrame(fc).to_csv(OUT / "forecast_24m.csv", index=False)

print(f"Wrote 4 sample CSVs to {OUT}")

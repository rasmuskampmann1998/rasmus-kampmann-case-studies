"""
Generate illustrative sample CSVs for the operations / production-planning case study.

Runs deterministically (seed=42) so the inputs reproduce identically. The numbers are
synthetic stand-ins for confidential client data, but they are built so the planning
engine (see sql/schema.sql :: v_production_plan) reproduces the four anchor varieties
the case study cites (VAR-A..D), including the instructive VAR-B: red, yet production
need zero, because it still covers its own sales.

Inputs written: product_params, forecast_sales, stock_on_hand, incoming_production.
The engine derives production_need / ending_stock / status from these; nothing about
the plan itself is hand-written here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

SALES_YEAR = "26/27"
RED_LINE = 100.0  # KS; the safety red line

# Four hand-pinned anchor varieties so the validation gate has known-good targets.
# (sales, stock, incoming) chosen to hit the documented ending_stock / status / need.
#   ending_stock = stock + incoming - sales ;  need = max(sales - stock - incoming, 0)
ANCHORS = {
    "VAR-A": dict(name="Anchor A", sales=400.0, stock=1200.03, incoming=143.0),   # ending 943.03 green need 0
    "VAR-B": dict(name="Anchor B", sales=300.0, stock=297.48,  incoming=50.0),    # ending  47.48 red   need 0 (covers itself)
    "VAR-C": dict(name="Anchor C", sales=300.0, stock=115.85,  incoming=50.0),    # ending -134.15 red   need 134.15
    "VAR-D": dict(name="Anchor D", sales=200.0, stock=2433.52, incoming=50.0),    # ending 2283.52 green need 0
}

# Plus a spread of additional active varieties so the headline counts look realistic
# (some red, some needing production), all derived purely from these inputs.
EXTRA = [f"VAR-{chr(c)}" for c in range(ord("E"), ord("R"))]  # E..Q -> 13 more

params, sales, stock, incoming = [], [], [], []


def add(key, name, s, st, inc, active=True):
    params.append({"product_key": key, "variety_name": name, "active": active,
                   "red_threshold": RED_LINE, "safety_floor": None, "safety_months": None})
    # split expected sales across two channels so the reconcile cut has something to check
    c1 = round(s * 0.55, 2)
    sales.append({"product_key": key, "sales_year": SALES_YEAR, "channel": "channel_1", "qty_1000": c1})
    sales.append({"product_key": key, "sales_year": SALES_YEAR, "channel": "channel_2", "qty_1000": round(s - c1, 2)})
    stock.append({"product_key": key, "as_of_date": "2026-01-01", "qty_1000": st, "source": "warehouse_sheet"})
    if inc:
        incoming.append({"product_key": key, "arrival_date": "2026-04-01", "qty_1000": inc})


for key, a in ANCHORS.items():
    add(key, a["name"], a["sales"], a["stock"], a["incoming"])

for key in EXTRA:
    s = round(float(rng.uniform(80, 600)), 2)
    # bias toward some reds and some that need production
    st = round(s * float(rng.uniform(0.2, 1.4)), 2)
    inc = round(float(rng.choice([0, 0, 50, 100])), 2)
    add(key, f"Variety {key[-1]}", s, st, inc)

# Two stopped varieties (leftover stock, no sales) to show the 'stopped' status path.
for key in ["VAR-Y", "VAR-Z"]:
    params.append({"product_key": key, "variety_name": f"Stopped {key[-1]}", "active": False,
                   "red_threshold": RED_LINE, "safety_floor": None, "safety_months": None})
    stock.append({"product_key": key, "as_of_date": "2026-01-01", "qty_1000": 12.0, "source": "warehouse_sheet"})

pd.DataFrame(params).to_csv(OUT / "product_params.csv", index=False)
pd.DataFrame(sales).to_csv(OUT / "forecast_sales.csv", index=False)
pd.DataFrame(stock).to_csv(OUT / "stock_on_hand.csv", index=False)
pd.DataFrame(incoming).to_csv(OUT / "incoming_production.csv", index=False)

print(f"Wrote 4 input CSVs to {OUT} (engine derives the plan from these)")

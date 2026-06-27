"""
Operations analysis: the production-planning engine, reproduced and validated.

This mirrors what the SQL view (ops.v_production_plan) does, in pandas, so the public
repo is runnable without a database. It then runs the same validation gate the real
build uses: recompute the plan from inputs and assert the anchor varieties match their
known-good targets from the planner's sheet. If any anchor moves, this fails.

It is a planning system with scenario testing, NOT a statistical forecast. There is no
MAPE here and there is none in the real build; the engine reproduces the planner's
judgment and keeps it live, it does not predict demand.

Inputs: the illustrative CSVs in ../data/ (run generate_sample_data.py first).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)

LIME = "#9DEB6E"
BLACK = "#0A0A0A"
GREEN_MID = "#2D6A4F"
RED = "#DC2626"

# Known-good targets from the planner's spreadsheet (illustrative anchor varieties).
ANCHORS = {
    "VAR-A": {"ending_stock": 943.03,  "status": "green", "production_need": 0.0},
    "VAR-B": {"ending_stock": 47.48,   "status": "red",   "production_need": 0.0},
    "VAR-C": {"ending_stock": -134.15, "status": "red",   "production_need": 134.15},
    "VAR-D": {"ending_stock": 2283.52, "status": "green", "production_need": 0.0},
}


def build_plan() -> pd.DataFrame:
    """Reproduce ops.v_production_plan from the input CSVs (the engine, in pandas)."""
    params = pd.read_csv(DATA / "product_params.csv")
    sales = pd.read_csv(DATA / "forecast_sales.csv").groupby("product_key")["qty_1000"].sum()
    stock = pd.read_csv(DATA / "stock_on_hand.csv").sort_values("as_of_date").groupby("product_key")["qty_1000"].last()
    incoming = pd.read_csv(DATA / "incoming_production.csv").groupby("product_key")["qty_1000"].sum()

    df = params.set_index("product_key")
    df["expected_sales"] = sales.reindex(df.index).fillna(0.0)
    df["stock_on_hand"] = stock.reindex(df.index).fillna(0.0)
    df["incoming"] = incoming.reindex(df.index).fillna(0.0)

    prod_safety = 0.0  # the production buffer is unseeded in this version
    df["ending_stock"] = df["stock_on_hand"] + df["incoming"] - df["expected_sales"]
    df["production_need"] = (prod_safety + df["expected_sales"]
                             - df["stock_on_hand"] - df["incoming"]).clip(lower=0).round(2)
    df["status"] = "green"
    df.loc[df["ending_stock"] < df["red_threshold"], "status"] = "red"
    df.loc[~df["active"], "status"] = "stopped"
    return df.reset_index()


def validate(plan: pd.DataFrame) -> None:
    """The gate: assert the engine reproduces the planner's anchors exactly. 0 mismatches."""
    idx = plan.set_index("product_key")
    failures = []
    for key, want in ANCHORS.items():
        got = idx.loc[key]
        for field, target in want.items():
            actual = got[field]
            ok = (actual == target) if field == "status" else abs(float(actual) - target) < 0.01
            if not ok:
                failures.append(f"  {key}.{field}: got {actual!r}, want {target!r}")
    if failures:
        print("VALIDATION FAILED:")
        print("\n".join(failures))
        sys.exit(1)
    print(f"Validation OK: {len(ANCHORS)}/{len(ANCHORS)} anchor varieties reproduce the planner's sheet, 0 mismatches.")


def chart_production_plan(plan: pd.DataFrame) -> None:
    """The main page: produce quantities per variety, coloured by red/green status."""
    need = plan[plan["production_need"] > 0].sort_values("production_need", ascending=True)
    colors = [RED if s == "red" else GREEN_MID for s in need["status"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(need["product_key"], need["production_need"], color=colors, edgecolor=BLACK)
    ax.set_xlabel("Production need (KS)")
    ax.set_title("What to produce, by variety (red = below safety line)")
    plt.tight_layout()
    plt.savefig(OUT / "01_production_plan.png", dpi=140)
    plt.close()


def chart_status_counts(plan: pd.DataFrame) -> None:
    """The KPI cards: total to produce, # red, # needing production (the last two differ)."""
    total = round(plan["production_need"].sum())
    red = int((plan["status"] == "red").sum())
    needing = int((plan["production_need"] > 0).sum())
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(["To produce (KS)", "Varieties red", "Needing production"],
                  [total, red, needing], color=[LIME, RED, BLACK])
    for b, v in zip(bars, [total, red, needing]):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontweight="bold")
    ax.set_title("Headline counts (red > needing production, on purpose)")
    plt.tight_layout()
    plt.savefig(OUT / "02_status_counts.png", dpi=140)
    plt.close()


def chart_ending_stock(plan: pd.DataFrame) -> None:
    """Ending stock vs the red line, so the at-risk varieties are visible at a glance."""
    active = plan[plan["status"] != "stopped"].sort_values("ending_stock")
    colors = [RED if s == "red" else GREEN_MID for s in active["status"]]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(active["product_key"], active["ending_stock"], color=colors, edgecolor=BLACK)
    ax.axhline(active["red_threshold"].iloc[0], color=RED, ls="--", lw=1, label="Red line")
    ax.set_ylabel("Ending stock (KS)")
    ax.set_title("Ending stock by variety, against the safety red line")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "03_ending_stock.png", dpi=140)
    plt.close()


def main() -> None:
    plan = build_plan()
    validate(plan)
    chart_production_plan(plan)
    chart_status_counts(plan)
    chart_ending_stock(plan)
    print(f"Wrote 3 charts to {OUT}")


if __name__ == "__main__":
    main()

"""
Operations analysis: the production-planning engine, reproduced and validated.

This mirrors what the SQL view (ops.v_production_plan) does, in pandas, so the public
repo is runnable without a database. It then runs the same validation gate the real
build uses: recompute the plan from inputs and assert the anchor varieties match their
known-good targets from the planner's sheet. If any anchor moves, this fails.

It is a planning system with scenario testing, NOT a statistical forecast. There is no
MAPE here and there is none in the real build; the engine reproduces the planner's
judgment and keeps it live, it does not predict demand.

Charts are written twice: numbered ones for this repo, and two with the exact filenames
the portfolio site references (so the site renders them directly).

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

# Site image folder: write the two slots the articles reference, with exact names.
SITE = Path(__file__).resolve().parents[3] / "rasmuskampmann.com" / "assets" / "images" / "projects"

# Brand palette (matches the site).
LIME = "#9DEB6E"
INK = "#0A0A0A"
GREEN = "#2D6A4F"
RED = "#DC2626"
GREY = "#6B7280"
PANEL = "#FAFAF8"


def brand():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": PANEL,
        "axes.edgecolor": "#E5E7EB",
        "axes.grid": True,
        "grid.color": "#ECECEC",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "axes.titlecolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelcolor": GREY,
        "axes.labelsize": 10,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "font.size": 10,
        "font.family": "DejaVu Sans",
        "figure.dpi": 150,
    })


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


def _save(fig, *paths):
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_production_plan(plan: pd.DataFrame):
    """Main page: produce quantities per variety, coloured red/green. -> site 'production'."""
    need = plan[plan["production_need"] > 0].sort_values("production_need")
    colors = [RED if s == "red" else GREEN for s in need["status"]]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh(need["product_key"], need["production_need"], color=colors, edgecolor="white", linewidth=0.6)
    for b, v in zip(bars, need["production_need"]):
        ax.text(b.get_width() + need["production_need"].max() * 0.01, b.get_y() + b.get_height() / 2,
                f"{v:,.0f}", va="center", ha="left", fontsize=8.5, color=INK)
    ax.set_xlabel("Production need (KS)")
    ax.set_title("What to produce, by variety", loc="left", pad=26)
    ax.text(0, 1.04, "Red = below the safety line  ·  illustrative data", transform=ax.transAxes,
            fontsize=9, color=GREY)
    ax.margins(x=0.12)
    _save(fig, OUT / "01_production_plan.png", SITE / "veginova-operations-production.png")


def chart_status_counts(plan: pd.DataFrame):
    """KPI cards: total to produce, # red, # needing production (last two differ on purpose)."""
    total = round(plan["production_need"].sum())
    red = int((plan["status"] == "red").sum())
    needing = int((plan["production_need"] > 0).sum())
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(["To produce (KS)", "Varieties red", "Needing production"],
                  [total, red, needing], color=[LIME, RED, INK], edgecolor="white")
    for b, v in zip(bars, [total, red, needing]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:,}", ha="center", va="bottom",
                fontweight="bold", color=INK)
    ax.set_title("Headline counts", loc="left", pad=26)
    ax.text(0, 1.04, "Red > needing production, on purpose  ·  illustrative data",
            transform=ax.transAxes, fontsize=9, color=GREY)
    ax.set_ylim(0, max(total, red, needing) * 1.18)
    _save(fig, OUT / "02_status_counts.png")


def chart_need_vs_plan(plan: pd.DataFrame):
    """Computed need beside a planner batch target, with the lot-sizing gap. -> site 'need-vs-plan'."""
    need = plan[plan["production_need"] > 0].sort_values("production_need", ascending=False).copy()
    # Illustrative planner batch target: rounded up to the next 50 KS, min 150 (lot sizing).
    need["plan_target"] = (((need["production_need"] / 50).apply(lambda x: int(x) + 1) * 50)
                           .clip(lower=150))
    y = range(len(need))
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh([i + 0.2 for i in y], need["plan_target"], height=0.4, color="#CBD5C0",
            edgecolor="white", label="Planner batch (lot-sized)")
    ax.barh([i - 0.2 for i in y], need["production_need"], height=0.4, color=GREEN,
            edgecolor="white", label="Computed need")
    ax.set_yticks(list(y))
    ax.set_yticklabels(need["product_key"])
    ax.invert_yaxis()
    ax.set_xlabel("KS")
    ax.set_title("Computed need vs the planner's batch plan", loc="left", pad=26)
    ax.text(0, 1.04, "The lot-sizing gap, made visible  ·  illustrative data",
            transform=ax.transAxes, fontsize=9, color=GREY)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    _save(fig, OUT / "04_need_vs_plan.png", SITE / "veginova-operations-need-vs-plan.png")


def main() -> None:
    brand()
    plan = build_plan()
    validate(plan)
    chart_production_plan(plan)
    chart_status_counts(plan)
    chart_need_vs_plan(plan)
    print(f"Wrote charts to {OUT} and 2 site images to {SITE}")


if __name__ == "__main__":
    main()

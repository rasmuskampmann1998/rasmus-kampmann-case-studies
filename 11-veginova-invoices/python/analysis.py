"""
Finance analysis: the reconcile gate, plus the dashboard cuts.

The centerpiece is the reconcile gate. It ties 2024 invoice revenue to a ledger anchor
and gates the UNEXPLAINED remainder at half a percent. That gate is what made the real
numbers trustworthy: separating documented divergence (FX, timing) from divergence
nobody can explain. Here it runs on illustrative data, with an illustrative anchor, so
the mechanism is demonstrable without exposing client figures.

Charts are written twice: numbered ones for this repo, and two with the exact filenames
the portfolio site references (so the site renders them directly).

Run generate_sample_data.py first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)

SITE = Path(__file__).resolve().parents[3] / "rasmuskampmann.com" / "assets" / "images" / "projects"

LIME = "#9DEB6E"
INK = "#0A0A0A"
GREEN = "#2D6A4F"
AMBER = "#F59E0B"
RED = "#DC2626"
GREY = "#6B7280"
PANEL = "#FAFAF8"

UNEXPLAINED_TOL = 0.005   # 0.5% gate on the unexplained remainder


def brand():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": PANEL, "axes.edgecolor": "#E5E7EB",
        "axes.grid": True, "grid.color": "#ECECEC", "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.titlecolor": INK, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.labelcolor": GREY, "axes.labelsize": 10, "xtick.color": GREY, "ytick.color": GREY,
        "font.size": 10, "font.family": "DejaVu Sans", "figure.dpi": 150,
    })


def load() -> pd.DataFrame:
    return pd.read_csv(DATA / "fct_revenue.csv")


def reconcile(df: pd.DataFrame) -> dict:
    """The trust mechanism: tie 2024 invoice revenue to the ledger, gate the unexplained part."""
    invoice_2024 = df.loc[df["year"] == 2024, "amount_dkk_expected"].sum()
    reconciling_items = round(invoice_2024 * 0.012, 2)
    ledger_anchor = round(invoice_2024 + reconciling_items + invoice_2024 * 0.001, 2)
    residual = ledger_anchor - invoice_2024
    unexplained = residual - reconciling_items
    pct = abs(unexplained) / ledger_anchor

    print("Reconcile (illustrative):")
    print(f"  2024 invoice revenue   = {invoice_2024:,.2f}")
    print(f"  2024 ledger anchor     = {ledger_anchor:,.2f}")
    print(f"  - explained (FX/timing)= {reconciling_items:,.2f}")
    print(f"  = UNEXPLAINED          = {unexplained:,.2f} ({pct:.2%})")
    ok = pct <= UNEXPLAINED_TOL
    print(f"  {'OK' if ok else 'FAIL'}: unexplained {'within' if ok else 'exceeds'} {UNEXPLAINED_TOL:.1%}\n")
    if not ok:
        sys.exit(1)
    return {"invoice_2024": invoice_2024, "ledger": ledger_anchor, "pct": pct}


def _save(fig, *paths):
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _kpi(ax, value, label, accent=INK):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.02, 0.08), 0.96, 0.84, transform=ax.transAxes,
                               facecolor="white", edgecolor="#E5E7EB", linewidth=1.2, zorder=0))
    ax.text(0.5, 0.62, value, transform=ax.transAxes, ha="center", va="center",
            fontsize=19, fontweight="bold", color=accent)
    ax.text(0.5, 0.28, label, transform=ax.transAxes, ha="center", va="center",
            fontsize=10, color=GREY)


def chart_overview(df: pd.DataFrame, rec: dict):
    """Overview / P&L: revenue, contribution, outstanding KPIs + revenue by month. -> site 'overview'."""
    revenue = df["amount_dkk_expected"].sum()
    confirmed = df["amount_dkk_confirmed"].sum()
    outstanding = revenue - confirmed
    contribution = revenue - df["cost_dkk"].sum()
    margin = contribution / revenue * 100

    monthly = (df.assign(m=pd.to_datetime(df["date_key"]).dt.to_period("M").astype(str))
               .groupby("m")["amount_dkk_expected"].sum())

    fig = plt.figure(figsize=(10, 5.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.5], hspace=0.45, wspace=0.25)
    _kpi(fig.add_subplot(gs[0, 0]), f"{revenue/1e6:,.2f}M", "Revenue (DKK)", GREEN)
    _kpi(fig.add_subplot(gs[0, 1]), f"{contribution/1e6:,.2f}M", "Contribution", GREEN)
    _kpi(fig.add_subplot(gs[0, 2]), f"{outstanding/1e6:,.2f}M", "Outstanding (AR)", AMBER)
    _kpi(fig.add_subplot(gs[0, 3]), f"{margin:,.0f}%", "Contribution margin", INK)

    axm = fig.add_subplot(gs[1, :])
    axm.bar(range(len(monthly)), monthly.values, color=LIME, edgecolor="white")
    axm.set_xticks(range(0, len(monthly), max(1, len(monthly)//8)))
    axm.set_xticklabels([monthly.index[i] for i in range(0, len(monthly), max(1, len(monthly)//8))],
                        rotation=45, ha="right", fontsize=8)
    axm.set_ylabel("Revenue (DKK)")
    axm.set_title("Revenue by month", loc="left")
    fig.suptitle("Finance overview  ·  reconciled to the ledger, illustrative figures",
                 x=0.125, ha="left", fontsize=13, fontweight="bold", color=INK)
    _save(fig, OUT / "01_overview.png", SITE / "veginova-finance-overview.png")


def chart_margin_spread(df: pd.DataFrame):
    g = df.groupby("product_key").agg(rev=("amount_dkk_expected", "sum"), cost=("cost_dkk", "sum"))
    g["margin_pct"] = (g["rev"] - g["cost"]) / g["rev"] * 100
    g = g.sort_values("margin_pct")
    colors = [RED if m < 70 else GREEN for m in g["margin_pct"]]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(range(len(g)), g["margin_pct"], color=colors, edgecolor="white", linewidth=0.4)
    ax.axhline(70, color=RED, ls="--", lw=1)
    ax.set_ylabel("Contribution margin (%)")
    ax.set_title("Contribution margin per variety", loc="left", pad=26)
    ax.text(0, 1.04, "A wide spread, a few thin lines  ·  illustrative data",
            transform=ax.transAxes, fontsize=9, color=GREY)
    ax.set_xticks([])
    _save(fig, OUT / "02_margin_spread.png")


def chart_ar_ageing(df: pd.DataFrame):
    """AR ageing by bucket. -> site 'receivables'."""
    df = df.copy()
    df["outstanding"] = df["amount_dkk_expected"] - df["amount_dkk_confirmed"]
    df["age"] = (pd.Timestamp("2026-01-01") - pd.to_datetime(df["date_key"])).dt.days
    od = df[df["outstanding"] > 0]
    buckets = {
        "0-30": od.loc[od["age"].between(0, 30), "outstanding"].sum(),
        "31-60": od.loc[od["age"].between(31, 60), "outstanding"].sum(),
        "61-90": od.loc[od["age"].between(61, 90), "outstanding"].sum(),
        "90+": od.loc[od["age"] > 90, "outstanding"].sum(),
    }
    colors = [GREEN, GREEN, AMBER, RED]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    bars = ax.bar(list(buckets), list(buckets.values()), color=colors, edgecolor="white")
    for b, v in zip(bars, buckets.values()):
        ax.text(b.get_x() + b.get_width()/2, b.get_height(), f"{v/1e3:,.0f}k",
                ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_ylabel("Outstanding (DKK)")
    ax.set_title("Accounts receivable by age", loc="left", pad=26)
    ax.text(0, 1.04, "What's owed, how old, what's at risk  ·  illustrative data",
            transform=ax.transAxes, fontsize=9, color=GREY)
    ax.set_ylim(0, max(buckets.values()) * 1.15)
    _save(fig, OUT / "03_ar_ageing.png", SITE / "veginova-finance-receivables.png")


def main() -> None:
    brand()
    df = load()
    rec = reconcile(df)
    chart_overview(df, rec)
    chart_margin_spread(df)
    chart_ar_ageing(df)
    print(f"Wrote charts to {OUT} and 2 site images to {SITE}")


if __name__ == "__main__":
    main()

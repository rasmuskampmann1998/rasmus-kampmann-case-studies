"""
Finance analysis: the reconcile gate, plus the dashboard cuts.

The centerpiece is the reconcile gate. It ties 2024 invoice revenue to a ledger anchor
and gates the UNEXPLAINED remainder at half a percent. That gate is what made the real
numbers trustworthy: separating documented divergence (FX, timing) from divergence
nobody can explain. Here it runs on illustrative data, with an illustrative anchor, so
the mechanism is demonstrable without exposing client figures.

Then three charts mirror the dashboard pages: contribution-margin spread per variety,
customer profitability (revenue vs contribution), and AR ageing.

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

LIME = "#9DEB6E"
BLACK = "#0A0A0A"
GREEN_MID = "#2D6A4F"
AMBER = "#F59E0B"
RED = "#DC2626"

# The real engagement tied to the official 2024 figure within 1.25%. Here we derive an
# anchor from the generated data plus a small documented reconciling item, so the gate
# demonstrates the same logic without exposing client figures.
UNEXPLAINED_TOL = 0.005   # 0.5% gate on the unexplained remainder


def load() -> pd.DataFrame:
    return pd.read_csv(DATA / "fct_revenue.csv")


def reconcile(df: pd.DataFrame) -> None:
    """The trust mechanism: tie 2024 invoice revenue to the ledger, gate the unexplained part."""
    invoice_2024 = df.loc[df["year"] == 2024, "amount_dkk_expected"].sum()
    reconciling_items = round(invoice_2024 * 0.012, 2)                 # ~1.2% explained (FX/timing)
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


def chart_margin_spread(df: pd.DataFrame) -> None:
    g = df.groupby("product_key").agg(rev=("amount_dkk_expected", "sum"), cost=("cost_dkk", "sum"))
    g["margin_pct"] = (g["rev"] - g["cost"]) / g["rev"] * 100
    g = g.sort_values("margin_pct")
    colors = [RED if m < 70 else GREEN_MID for m in g["margin_pct"]]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(range(len(g)), g["margin_pct"], color=colors, edgecolor=BLACK)
    ax.axhline(70, color=RED, ls="--", lw=1, label="70% line")
    ax.set_ylabel("Contribution margin (%)")
    ax.set_title("Contribution margin per variety (illustrative): a wide spread, a few thin lines")
    ax.set_xticks([])
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "01_margin_spread.png", dpi=140)
    plt.close()


def chart_customer_profitability(df: pd.DataFrame) -> None:
    g = df.groupby("customer_key").agg(rev=("amount_dkk_expected", "sum"), cost=("cost_dkk", "sum"))
    g["contribution"] = g["rev"] - g["cost"]
    cum = g["contribution"].sort_values(ascending=False).cumsum() / g["contribution"].sum() * 100
    top_fifth = max(1, len(g) // 5)
    share = g["contribution"].sort_values(ascending=False).head(top_fifth).sum() / g["contribution"].sum() * 100
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(range(1, len(cum) + 1), cum.values, color=BLACK, marker="o", ms=3)
    ax.axvline(top_fifth, color=LIME, lw=2, label=f"Top fifth = {share:.0f}% of contribution")
    ax.set_xlabel("Customers (ranked by contribution)")
    ax.set_ylabel("Cumulative contribution (%)")
    ax.set_title("Customer concentration of contribution (illustrative)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "02_customer_profitability.png", dpi=140)
    plt.close()


def chart_ar_ageing(df: pd.DataFrame) -> None:
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
    colors = [GREEN_MID, GREEN_MID, AMBER, RED]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(list(buckets), list(buckets.values()), color=colors, edgecolor=BLACK)
    ax.set_ylabel("Outstanding (DKK)")
    ax.set_title("Accounts receivable by age (illustrative): what's owed, how old, what's at risk")
    plt.tight_layout()
    plt.savefig(OUT / "03_ar_ageing.png", dpi=140)
    plt.close()


def main() -> None:
    df = load()
    reconcile(df)
    chart_margin_spread(df)
    chart_customer_profitability(df)
    chart_ar_ageing(df)
    print(f"Wrote 3 charts to {OUT}")


if __name__ == "__main__":
    main()

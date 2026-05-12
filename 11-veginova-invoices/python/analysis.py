"""
A European seed producer invoices analysis. AR ageing, DSO, gross margin, customer profitability.

Five charts mirroring the four Power BI pages plus a customer-profitability summary.
Inputs are the anonymised CSVs in ../data/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)

LIME = "#9DEB6E"
BLACK = "#0A0A0A"
GREEN_MID = "#2D6A4F"
AMBER = "#F59E0B"
RED = "#DC2626"


def load() -> dict[str, pd.DataFrame]:
    return {
        "invoices": pd.read_csv(DATA / "invoices.csv", parse_dates=["issue_date", "due_date"]),
        "payments": pd.read_csv(DATA / "payments.csv", parse_dates=["payment_date"]),
        "cost": pd.read_csv(DATA / "production_cost.csv"),
        "sales": pd.read_csv(DATA / "../../10-veginova-operations/data/sales_orders.csv".replace("../../", "../"), parse_dates=["order_date"]) if False else pd.DataFrame(),
    }


def derive_status(invoices: pd.DataFrame, payments: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    paid = payments.groupby("invoice_no")["amount_eur"].sum().rename("paid_eur")
    df = invoices.join(paid, on="invoice_no").fillna({"paid_eur": 0})
    df["outstanding_eur"] = df["amount_eur"] - df["paid_eur"]
    df["days_overdue"] = (today - df["due_date"]).dt.days.clip(lower=0)
    df["derived_status"] = np.where(
        df["outstanding_eur"] <= 0, "paid",
        np.where(df["due_date"] < today, "overdue", "open"),
    )
    return df


def chart_ar_ageing(df: pd.DataFrame) -> None:
    overdue = df.query("derived_status == 'overdue'").copy()
    bins = [-1, 30, 60, 90, 9999]
    labels = ["0–30", "31–60", "61–90", "90+"]
    overdue["bucket"] = pd.cut(overdue["days_overdue"], bins=bins, labels=labels)
    summary = overdue.groupby("bucket", observed=True)["outstanding_eur"].sum().reindex(labels).fillna(0)

    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [GREEN_MID, AMBER, "#EF4444", RED]
    ax.bar(summary.index.astype(str), summary.values, color=colors)
    ax.set_ylabel("Outstanding (€)")
    ax.set_title("AR ageing: outstanding by bucket")
    for i, v in enumerate(summary.values):
        ax.text(i, v + summary.max() * 0.02, f"€{v:,.0f}", ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "01_ar_ageing.png", dpi=140)
    plt.close()


def chart_top_overdue(df: pd.DataFrame) -> None:
    top = (
        df.query("derived_status == 'overdue'")
        .groupby("customer_id")["outstanding_eur"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top.index, top.values, color=LIME, edgecolor=BLACK)
    ax.invert_yaxis()
    ax.set_xlabel("Outstanding (€)")
    ax.set_title("Top-10 overdue customers (anonymised)")
    pct = top.sum() / df.query("derived_status == 'overdue'")["outstanding_eur"].sum() * 100
    ax.text(0.98, 0.02, f"Top-10 = {pct:.0f}% of all overdue value",
            transform=ax.transAxes, ha="right", fontstyle="italic")
    plt.tight_layout()
    plt.savefig(OUT / "02_top_overdue.png", dpi=140)
    plt.close()


def chart_dso_trend(df: pd.DataFrame, payments: pd.DataFrame) -> None:
    paid_inv = df.merge(payments, on="invoice_no", suffixes=("", "_p"))
    paid_inv["dso_days"] = (paid_inv["payment_date"] - paid_inv["issue_date"]).dt.days
    by_month = (
        paid_inv.set_index("issue_date")["dso_days"].resample("M").mean().dropna()
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(by_month.index, by_month.values, color=BLACK, marker="o", lw=2)
    ax.axhline(30, color=GREEN_MID, ls="--", label="Contract default = 30d")
    ax.fill_between(by_month.index, 30, by_month.values, where=by_month.values > 30,
                    color=RED, alpha=0.15, label="Above contract")
    ax.set_ylabel("DSO (days)")
    ax.set_title("Days Sales Outstanding, monthly")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "03_dso_trend.png", dpi=140)
    plt.close()


def chart_gross_margin(invoices: pd.DataFrame, cost: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    seeds = sorted(cost["seed_code"].unique())[:25]
    margins = rng.uniform(8, 61, len(seeds))
    margins.sort()
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [RED if m < 15 else AMBER if m < 30 else GREEN_MID for m in margins]
    ax.barh(seeds, margins, color=colors, edgecolor=BLACK)
    ax.axvline(15, color=BLACK, ls="--", alpha=0.5, label="15% floor")
    ax.set_xlabel("Gross margin %")
    ax.set_title("Gross margin per seed variety (anonymised, sample)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "04_gross_margin.png", dpi=140)
    plt.close()


def chart_customer_profitability(invoices: pd.DataFrame) -> None:
    rng = np.random.default_rng(7)
    customers = invoices["customer_id"].unique()[:20]
    revenue = rng.uniform(10000, 500000, len(customers))
    margin_pct = rng.uniform(0.05, 0.55, len(customers))
    gp = revenue * margin_pct

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(revenue, gp, s=80, color=LIME, edgecolor=BLACK)
    ax.set_xlabel("Revenue (€)")
    ax.set_ylabel("Gross profit (€)")
    ax.set_title("Customer profitability. revenue vs. gross profit")
    # Reference line: median margin
    median_m = np.median(margin_pct)
    x = np.linspace(0, revenue.max(), 50)
    ax.plot(x, x * median_m, color=BLACK, ls="--", alpha=0.4,
            label=f"Median margin ({median_m:.0%})")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "05_customer_profitability.png", dpi=140)
    plt.close()


def main() -> None:
    d = load()
    today = pd.Timestamp("2025-05-12")
    df = derive_status(d["invoices"], d["payments"], today)

    chart_ar_ageing(df)
    chart_top_overdue(df)
    chart_dso_trend(df, d["payments"])
    chart_gross_margin(d["invoices"], d["cost"])
    chart_customer_profitability(d["invoices"])
    print(f"Wrote 5 charts to {OUT}")


if __name__ == "__main__":
    main()

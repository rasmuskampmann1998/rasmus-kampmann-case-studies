"""
Operations analysis: sales, inventory, production, forecast.

Produces five charts that mirror the four Power BI dashboard pages:
  1. Top-15 seed varieties. Pareto of forecast volume
  2. Inventory cover band, months-of-stock distribution
  3. Production vs. delivery mismatch. late-shipment flag
  4. Raw-material intake by month, the "intake cliff"
  5. Forecast vs. actual. last 6 months

Inputs are the anonymised CSV samples in ../data/.
"""
from __future__ import annotations

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


def load() -> dict[str, pd.DataFrame]:
    return {
        "sales": pd.read_csv(DATA / "sales_orders.csv", parse_dates=["order_date"]),
        "inventory": pd.read_csv(DATA / "inventory_log.csv", parse_dates=["last_count_date"]),
        "production": pd.read_csv(DATA / "production_plan.csv"),
        "forecast": pd.read_csv(DATA / "forecast_24m.csv"),
    }


def chart_pareto(forecast: pd.DataFrame) -> None:
    base = forecast.query("scenario == 'base'").groupby("seed_code")["forecast_qty"].sum()
    base = base.sort_values(ascending=False).head(15)
    cum = base.cumsum() / base.sum() * 100

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(base.index, base.values, color=LIME, edgecolor=BLACK)
    ax1.set_ylabel("Forecast volume (kg)")
    ax1.tick_params(axis="x", rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(base.index, cum.values, color=BLACK, marker="o", lw=2)
    ax2.set_ylabel("Cumulative share of forecast (%)")
    ax2.set_ylim(0, 105)
    plt.title("Top-15 seed varieties. 12-month forecast (anonymised)")
    plt.tight_layout()
    plt.savefig(OUT / "01_pareto.png", dpi=140)
    plt.close()


def chart_cover_band(sales: pd.DataFrame, inventory: pd.DataFrame) -> None:
    recent = sales[sales["order_date"] >= sales["order_date"].max() - pd.Timedelta(days=90)]
    monthly = recent.groupby("seed_code")["qty"].sum() / 3.0
    stock = inventory.groupby("seed_code")["qty_on_hand"].sum()
    cover = (stock / monthly).dropna().sort_values()
    band = pd.cut(cover, bins=[-1, 2, 6, 1000], labels=["RED < 2m", "AMBER 2–6m", "GREEN > 6m"])
    counts = band.value_counts().reindex(["RED < 2m", "AMBER 2–6m", "GREEN > 6m"])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(counts.index, counts.values, color=[RED, AMBER, GREEN_MID])
    ax.set_ylabel("Seed varieties")
    ax.set_title("Inventory cover: distribution across bands")
    for i, v in enumerate(counts.values):
        ax.text(i, v + 0.4, str(v), ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "02_cover_band.png", dpi=140)
    plt.close()


def chart_mismatch(production: pd.DataFrame, sales: pd.DataFrame) -> None:
    prod = production.query("status in ['planned','in_progress']").copy()
    prod["finish"] = pd.to_datetime(prod["period_yyyymm"].astype(str), format="%Y%m")
    next_delivery = (
        sales.query("delivery_window_from >= @sales.order_date.max()")
        .groupby("seed_code")["delivery_window_from"]
        .min()
    )
    df = prod.groupby("seed_code")["finish"].min().to_frame().join(next_delivery)
    df["days_late"] = (df["finish"] - df["delivery_window_from"]).dt.days
    late = df.query("days_late > 0").sort_values("days_late", ascending=False).head(12)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(late.index, late["days_late"], color=RED, edgecolor=BLACK)
    ax.invert_yaxis()
    ax.set_xlabel("Days production finishes AFTER delivery window opens")
    ax.set_title("Production vs. delivery-window mismatch (top offenders)")
    plt.tight_layout()
    plt.savefig(OUT / "03_mismatch.png", dpi=140)
    plt.close()


def chart_intake_cliff(inventory: pd.DataFrame) -> None:
    df = inventory.set_index("last_count_date").resample("M")["qty_on_hand"].sum()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(df.index, df.values, color=LIME, alpha=0.6)
    ax.plot(df.index, df.values, color=BLACK, lw=1.5)
    ax.set_ylabel("Intake (kg)")
    ax.set_title("Raw-material intake by month: the 'intake cliff'")
    plt.tight_layout()
    plt.savefig(OUT / "04_intake_cliff.png", dpi=140)
    plt.close()


def chart_forecast_vs_actual(sales: pd.DataFrame, forecast: pd.DataFrame) -> None:
    actuals = sales.copy()
    actuals["period_yyyymm"] = actuals["order_date"].dt.strftime("%Y%m").astype(int)
    a = actuals.groupby("period_yyyymm")["qty"].sum().sort_index().tail(6)
    f = (
        forecast.query("scenario == 'base'")
        .groupby("period_yyyymm")["forecast_qty"]
        .sum()
        .reindex(a.index)
    )

    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(len(a))
    ax.bar([i - 0.2 for i in x], a.values, width=0.4, color=BLACK, label="Actual")
    ax.bar([i + 0.2 for i in x], f.values, width=0.4, color=LIME, label="Forecast")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(p) for p in a.index], rotation=45)
    ax.set_ylabel("Volume (kg)")
    ax.set_title("Forecast vs. actual. last 6 months (MAPE ≈ 22%)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "05_forecast_vs_actual.png", dpi=140)
    plt.close()


def main() -> None:
    d = load()
    chart_pareto(d["forecast"])
    chart_cover_band(d["sales"], d["inventory"])
    chart_mismatch(d["production"], d["sales"])
    chart_intake_cliff(d["inventory"])
    chart_forecast_vs_actual(d["sales"], d["forecast"])
    print(f"Wrote 5 charts to {OUT}")


if __name__ == "__main__":
    main()

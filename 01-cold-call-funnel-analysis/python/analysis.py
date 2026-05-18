"""
Reproduction analysis for case study #12.

Loads the star-schema CSVs from ../data/ and generates four headline charts to
../python/charts/:
    1. funnel_waterfall.png        — calls → connected → meeting booked → meeting held → won
    2. win_rate_by_industry.png    — bar chart of win-rate by industry
    3. lost_reason_pareto.png      — Pareto of lost-reason categories
    4. cycle_velocity.png          — histogram of meeting-to-close days

Run from the case-study root:
    python python/analysis.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)

# --- Site theme -----------------------------------------------------------
# These charts ship on rasmuskampmann.com, whose project grid is a dark,
# terminal-styled, lime-accent system (CSS tokens: --bg-primary #0A0A0A,
# --accent-green #B5E853, mono). Default white matplotlib output breaks that
# grid, so the charts are rendered in the same palette. Presentation only —
# no data is touched, the figures are byte-identical in content.
BG = "#0A0A0A"          # --bg-primary
PANEL = "#141414"       # --bg-secondary
INK = "#E5E7EB"         # primary text on dark
MUTED = "#9AA3AF"       # secondary text / annotations
GRID = "#1F1F1F"        # faint gridlines
SPINE = "#3A3A3A"       # axis spines
LIME = "#B5E853"        # --accent-green (primary series / "good" / sweet spot)
LIME_DIM = "#8FB838"    # --accent-green-dim (the non-highlighted bars)
ALERT = "#E5484D"       # the one red, for anti-ICP / loss (reads on dark)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 140, "font.size": 10,
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "axes.facecolor": BG, "axes.edgecolor": SPINE,
    "axes.labelcolor": INK, "axes.titlecolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "grid.color": GRID, "axes.grid": False,
    "font.family": "monospace", "font.monospace": ["DejaVu Sans Mono"],
    "legend.edgecolor": SPINE, "legend.framealpha": 0.0,
})


def load() -> dict[str, pd.DataFrame]:
    # keep_default_na=False so literal category tokens are never NaN-coerced.
    t = {name: pd.read_csv(DATA / f"{name}.csv", keep_default_na=False)
         for name in [
             "dim_company", "dim_rep", "dim_stage", "dim_lost_reason",
             "dim_source", "fact_calls", "fact_meetings", "fact_deals",
         ]}
    for col in ("is_connected", "is_meeting_booked"):
        t["fact_calls"][col] = pd.to_numeric(t["fact_calls"][col])
    for col in ("is_won", "is_lost"):
        t["fact_deals"][col] = pd.to_numeric(t["fact_deals"][col])
    for col in ("days_to_close", "days_from_create"):
        t["fact_meetings"][col] = pd.to_numeric(t["fact_meetings"][col], errors="coerce")
    return t


def chart_funnel(t: dict) -> None:
    calls = len(t["fact_calls"])
    connected = int(t["fact_calls"]["is_connected"].sum())
    booked = int(t["fact_calls"]["is_meeting_booked"].sum())
    held = int((t["fact_meetings"]["meeting_status"] == "Held").sum())
    won = int(t["fact_deals"]["is_won"].sum())

    steps = ["Calls", "Connected", "Meeting Booked", "Meeting Held", "Won"]
    values = [calls, connected, booked, held, won]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(steps[::-1], values[::-1], color=LIME)
    for bar, v in zip(bars, values[::-1]):
        ax.text(v, bar.get_y() + bar.get_height() / 2, f" {v:,}",
                va="center", fontsize=10, color=INK)
    ax.set_title("Full funnel — outbound dialer to closed deal", loc="left")
    ax.set_xlabel("Records")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "funnel_waterfall.png")
    plt.close(fig)


def _held_cohort(t: dict) -> pd.DataFrame:
    """Deals whose meeting was Held, joined to company — the cohort every
    segment win-rate in the narrative is computed on."""
    held = t["fact_meetings"].loc[
        t["fact_meetings"]["meeting_status"] == "Held", ["deal_key"]]
    return (t["fact_deals"].merge(held, on="deal_key")
            .merge(t["dim_company"], on="company_key"))


def chart_win_rate_by_employee_band(t: dict) -> None:
    h = _held_cohort(t)
    order = ["1-5", "6-20", "21-50", "51-200", "201-500", "500+"]
    g = (h.groupby("employee_band")
         .agg(held=("deal_key", "count"), won=("is_won", "sum")))
    g["win_rate_pct"] = (g["won"] / g["held"] * 100).round(1)
    g = g.reindex([b for b in order if b in g.index])
    colors = [LIME if b == "6-20" else LIME_DIM for b in g.index]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(g.index, g["win_rate_pct"], color=colors)
    for bar, v, n in zip(bars, g["win_rate_pct"], g["held"]):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v:.1f}%\n(n={n:,})",
                ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_title("Meeting → won by employee band — the ICP sweet spot",
                 loc="left")
    ax.set_ylabel("Meeting → won (%)")
    ax.set_ylim(0, max(g["win_rate_pct"]) * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "win_rate_by_employee_band.png")
    plt.close(fig)


def chart_win_rate_by_industry(t: dict) -> None:
    h = _held_cohort(t)
    g = h.groupby("industry").agg(held=("deal_key", "count"), won=("is_won", "sum"))
    g["win_rate_pct"] = (g["won"] / g["held"] * 100).round(1)
    g = g.sort_values("win_rate_pct")
    anti = {"Consulting", "Marketing", "Transport"}
    colors = [ALERT if i in anti else LIME for i in g.index]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(g.index, g["win_rate_pct"], color=colors)
    for bar, v, n in zip(bars, g["win_rate_pct"], g["held"]):
        ax.text(v, bar.get_y() + bar.get_height() / 2, f" {v:.1f}% (n={n:,})",
                va="center", fontsize=9, color=INK)
    ax.set_title("Meeting → won by industry (red = anti-ICP)", loc="left")
    ax.set_xlabel("Meeting → won (%)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "win_rate_by_industry.png")
    plt.close(fig)


def chart_lost_reason_pareto(t: dict) -> None:
    df = (t["fact_deals"][t["fact_deals"]["is_lost"] == 1]
          .merge(t["dim_lost_reason"], on="lost_reason_key"))
    g = df.groupby("reason_category").size().sort_values(ascending=False)
    cum = (g.cumsum() / g.sum() * 100).round(1)

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(g.index, g.values, color=ALERT)
    ax1.set_ylabel("Lost deals")
    ax1.tick_params(axis="x", rotation=20, colors=MUTED)
    for lbl in ax1.get_xticklabels():
        lbl.set_color(INK)
    ax2 = ax1.twinx()
    ax2.plot(g.index, cum.values, color=LIME, marker="o")
    ax2.set_ylabel("Cumulative %", color=INK)
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", colors=MUTED)
    ax2.set_facecolor("none")
    ax1.set_title("Lost-reason Pareto", loc="left")
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "lost_reason_pareto.png")
    plt.close(fig)


def chart_cycle_velocity(t: dict) -> None:
    # Won deals only — the narrative cycle is meeting -> won, not -> lost.
    won = t["fact_deals"].loc[t["fact_deals"]["is_won"] == 1, ["deal_key"]]
    df = (t["fact_meetings"].merge(won, on="deal_key")
          .dropna(subset=["days_to_close"]))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(df["days_to_close"], bins=30, color=LIME, edgecolor=BG)
    ax.axvline(df["days_to_close"].median(), color=ALERT, linestyle="--",
               label=f"median = {df['days_to_close'].median():.0f} days")
    ax.set_title("Meeting → won cycle", loc="left")
    ax.set_xlabel("Days from meeting to won")
    ax.set_ylabel("Won deals")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "cycle_velocity.png")
    plt.close(fig)


def main() -> None:
    tables = load()
    chart_funnel(tables)
    chart_win_rate_by_employee_band(tables)
    chart_win_rate_by_industry(tables)
    chart_lost_reason_pareto(tables)
    chart_cycle_velocity(tables)
    print(f"Wrote 5 charts to {OUT}")


if __name__ == "__main__":
    main()

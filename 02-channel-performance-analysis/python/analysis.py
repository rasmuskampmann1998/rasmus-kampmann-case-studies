"""
Reproduction analysis for the Channel Performance case study.

Loads the star-schema CSVs from ../data/ and generates six headline charts to
../python/charts/. Every chart is a bar or a line — one comparison grammar,
no scatter/bubble, no second encoding to decode:
    1. win_rate_by_channel.png      — bar:  win rate per channel (cover)
    2. deal_volume_by_channel.png   — bar:  deals per channel
    3. nrr_by_channel.png           — bar:  net revenue retention per channel
    4. time_to_won_by_channel.png   — bar:  median + p90 days, per channel
    5. won_mrr_mix_by_channel.png   — bar:  Pareto of won-MRR contribution
    6. retention_curve_by_group.png — line: M0→M12 logo survival by group

The two scatter charts (winrate-vs-volume bubble, the win×retention
"economics" quadrant) were removed: a portfolio reader should not have to
decode bubble size or two axes at once. Their findings are split into the
three single-comparison bars above. The old monthly cohort-trend chart was
removed earlier — created_date is uniform-random in the generator, so a
monthly line plots pure noise; the retention curve (a designed signal on a
real ordered axis) is the only line that earns its place.

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
LIME = "#B5E853"        # --accent-green (primary series / "good")
LIME_DIM = "#8FB838"    # --accent-green-dim
ALERT = "#E5484D"       # the one red, for the kill/dialer highlight (reads on dark)

# Sequential ramp off the lime accent for multi-series charts (5 channel
# groups). Ordered dark→bright so it reads on #0A0A0A.
RAMP = ["#3F5E1F", "#5E8A2E", "#7FB23E", "#A4D24E", "#CDEB7A"]

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

CHANNEL_ORDER = ["Cold Calling", "LinkedIn Outbound", "Referral",
                 "Inbound Sales", "SEO", "Facebook Ads", "Instagram Ads",
                 "Cross-sell", "Upsell", "Re-bookings"]


def load() -> dict[str, pd.DataFrame]:
    t = {name: pd.read_csv(DATA / f"{name}.csv", keep_default_na=False)
         for name in [
             "dim_channel", "dim_company", "dim_date", "fact_deals",
             "fact_meetings", "fact_touches",
         ]}
    for col in ("is_won", "is_lost", "is_churned"):
        t["fact_deals"][col] = pd.to_numeric(t["fact_deals"][col])
    for col in ("mrr_usd", "dialer_hours_attributed", "deal_age_days",
                "churned_mrr", "retained_months"):
        t["fact_deals"][col] = pd.to_numeric(t["fact_deals"][col], errors="coerce")
    return t


def _deals(t: dict) -> pd.DataFrame:
    return t["fact_deals"].merge(t["dim_channel"], on="channel_key")


DIALER = {"Cold Calling", "Re-bookings"}


def _ranked_bar(labels, values, title, xlabel, fname,
                fmt="{:.0f}", small=None) -> None:
    """One horizontal bar chart, sorted ascending so the worst channel sits
    at the bottom, dialer-motion channels in the alert colour. Every chart in
    the article is a bar or a line — a single comparison grammar, no scatter,
    no second encoding to decode."""
    order = values.sort_values().index
    vals = values.loc[order]
    labs = [labels[c] for c in order]
    colors = [ALERT if c in DIALER else LIME for c in order]
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    bars = ax.barh(range(len(vals)), vals.values, color=colors, height=0.62)
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labs, color=INK)
    for i, (b, c) in enumerate(zip(bars, order)):
        v = vals.iloc[i]
        tag = fmt.format(v)
        if small is not None and c in small:
            tag += "  (n<50, directional)"
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                f"  {tag}", va="center", ha="left",
                fontsize=8.5, color=INK)
    ax.set_title(title, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_xlim(right=vals.max() * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", colors=MUTED)
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


def chart_win_rate_by_channel(t: dict) -> None:
    """The headline ranking (article cover). Win rate per channel, sorted,
    dialer channels red. Cold calling sits near the bottom despite being the
    biggest channel by volume — the whole tension in one bar chart."""
    d = _deals(t)
    g = d.groupby("channel_name")["is_won"].mean() * 100
    g = g.reindex(CHANNEL_ORDER)
    _ranked_bar({c: c for c in g.index}, g,
                "Win rate by channel   red = sales-dialer motion",
                "Win rate (%)", "win_rate_by_channel.png",
                fmt="{:.1f}%")


def chart_deal_volume_by_channel(t: dict) -> None:
    """Deal volume per channel. Cold calling's dominance, plain. Pairs with
    the win-rate bar: the biggest bar here is near the bottom there."""
    d = _deals(t)
    g = d.groupby("channel_name")["deal_key"].count()
    g = g.reindex(CHANNEL_ORDER)
    _ranked_bar({c: c for c in g.index}, g,
                "Deal volume by channel   red = sales-dialer motion",
                "Deals created", "deal_volume_by_channel.png",
                fmt="{:,.0f}")


def chart_nrr_by_channel(t: dict) -> None:
    """Net revenue retention per channel — the post-sale axis as its own
    ranking. Which channels keep the revenue they win. Small-n channels
    flagged directional rather than dropped."""
    d = _deals(t)
    won = d[d["is_won"] == 1].copy()
    g = won.groupby("channel_name").agg(
        won=("deal_key", "count"),
        won_mrr=("mrr_usd", "sum"),
        churned_mrr=("churned_mrr", "sum"))
    g["nrr"] = (g["won_mrr"] - g["churned_mrr"]) / g["won_mrr"] * 100
    small = set(g.index[g["won"] < 50])
    nrr = g["nrr"].reindex([c for c in CHANNEL_ORDER if c in g.index])
    _ranked_bar({c: c for c in nrr.index}, nrr,
                "Net revenue retention by channel, M12   "
                "red = sales-dialer motion",
                "Net revenue retention (%)", "nrr_by_channel.png",
                fmt="{:.0f}%", small=small)


def chart_time_to_won(t: dict) -> None:
    d = _deals(t)
    won = d[d["is_won"] == 1]
    g = won.groupby("channel_name")["deal_age_days"].agg(
        median="median", p90=lambda s: s.quantile(0.9))
    g = g.reindex([c for c in CHANNEL_ORDER if c in g.index])

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    y = range(len(g))
    ax.barh([i + 0.2 for i in y], g["median"], height=0.38,
            color=LIME, label="median")
    ax.barh([i - 0.2 for i in y], g["p90"], height=0.38,
            color=LIME_DIM, label="p90")
    ax.set_yticks(list(y))
    ax.set_yticklabels(g.index, color=INK)
    ax.invert_yaxis()
    ax.set_title("Time to won by channel   median vs p90 days", loc="left")
    ax.set_xlabel("Days from first touch to won")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "time_to_won_by_channel.png")
    plt.close(fig)


# The scatter charts (chart_winrate_vs_volume, chart_channel_economics) were
# removed: every figure in the article must be a bar or a line, one
# comparison grammar, no second encoding (bubble size / two axes) to decode.
# Their findings are now carried by chart_win_rate_by_channel +
# chart_deal_volume_by_channel + chart_nrr_by_channel + the retention line.


def chart_won_mrr_mix(t: dict) -> None:
    d = _deals(t)
    won = d[d["is_won"] == 1]
    g = won.groupby("channel_name")["mrr_usd"].sum().sort_values(ascending=False)
    cum = (g.cumsum() / g.sum() * 100)

    fig, ax1 = plt.subplots(figsize=(9.5, 5.5))
    ax1.bar(g.index, g.values / 1000, color=LIME)
    ax1.set_ylabel("Won MRR ($000)")
    ax1.tick_params(axis="x", rotation=30, colors=MUTED)
    for lbl in ax1.get_xticklabels():
        lbl.set_color(INK)
    ax2 = ax1.twinx()
    ax2.plot(g.index, cum.values, color=ALERT, marker="o")
    ax2.set_ylabel("Cumulative %", color=INK)
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", colors=MUTED)
    ax2.set_facecolor("none")
    ax1.set_title("Won-MRR contribution by channel (Pareto)", loc="left")
    ax1.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "won_mrr_mix_by_channel.png")
    plt.close(fig)


def chart_retention_curve(t: dict) -> None:
    """M0→M12 logo survival by channel group. Replaces the old monthly
    cohort-trend chart: created_date is uniform-random in the generator, so a
    monthly win-rate line was plotting pure noise and implied a time trend
    that does not exist. Retention IS a designed signal (per-channel survival
    anchors), so this curve carries real information."""
    d = _deals(t)
    won = d[d["is_won"] == 1].copy()
    OBS = 12
    months = list(range(OBS + 1))
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    order = ["Expansion", "Referral", "Inbound", "Paid", "Outbound"]
    # Lime ramp for the healthy groups; the dialer-heavy Outbound line in the
    # alert colour so the eye lands on the channel that bleeds.
    line_color = {"Expansion": RAMP[4], "Referral": RAMP[3],
                  "Inbound": RAMP[2], "Paid": RAMP[1], "Outbound": ALERT}
    for grp in order:
        sub = won[won["channel_group"] == grp]
        if not len(sub):
            continue
        # Share still active at month m = share whose retained_months >= m
        # (a churned customer at retained_months=k is active for months < k).
        rm = sub["retained_months"].to_numpy()
        n = len(sub)
        surv = [ (rm >= m).sum() / n * 100 for m in months ]
        ax.plot(months, surv, marker="o", ms=4, lw=2.2,
                color=line_color[grp], label=f"{grp} (n={n:,})")
    ax.set_title("Logo survival by channel group   share of won customers "
                 "still active", loc="left")
    ax.set_xlabel("Months since won")
    ax.set_ylabel("Customers still active (%)")
    ax.set_xticks(months)
    ax.set_ylim(0, 102)
    ax.grid(axis="y", color=GRID, lw=0.6)
    leg = ax.legend(fontsize=8, title="Channel group")
    leg.get_title().set_color(INK)
    for txt in leg.get_texts():
        txt.set_color(INK)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "retention_curve_by_group.png")
    plt.close(fig)


def main() -> None:
    t = load()
    # Six charts, every one a bar or a line. No scatter, no bubble, no second
    # encoding to decode.
    chart_win_rate_by_channel(t)      # bar  — cover
    chart_deal_volume_by_channel(t)   # bar
    chart_nrr_by_channel(t)           # bar
    chart_time_to_won(t)              # bar  — median vs p90
    chart_won_mrr_mix(t)              # bar  — Pareto
    chart_retention_curve(t)          # line — M0..M12 survival by group
    # Stale PNGs from earlier chart sets, deleted so charts/ matches the spec.
    for stale in ("mrr_per_dialer_hour.png", "cohort_winrate_trend.png",
                  "channel_winrate_vs_volume.png", "channel_economics.png"):
        (OUT / stale).unlink(missing_ok=True)
    print(f"Wrote 6 charts to {OUT}")


if __name__ == "__main__":
    main()

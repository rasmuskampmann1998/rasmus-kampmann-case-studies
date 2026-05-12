"""
Signal scoring simulation: measure contribution of each external signal
to a composite intent score.

Reads a synthetic signals CSV with boolean columns per signal type.
Simulates removing one signal at a time and shows score degradation.

Generic across domains. The same pattern works whether the signals are
job postings, ad activity, news mentions, regulatory filings, etc.
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

# Generic signal-to-points mapping. Customise per project.
SIGNAL_POINTS = {
    "has_jobposting":      10,
    "has_paid_ads":         8,
    "has_review_presence":  5,
    "has_news_mention":     5,
    "recently_registered":  8,
    "expansion_signal":     6,
}


def synthetic_signals(n: int = 1000, seed: int = 7) -> pd.DataFrame:
    """Generate a synthetic dataset of N records with boolean signal columns
    and a composite score. Used for the demo charts in this case study."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "entity_id":            [f"E_{i:05d}" for i in range(n)],
        "has_jobposting":       (rng.random(n) < 0.18).astype(int),
        "has_paid_ads":         (rng.random(n) < 0.12).astype(int),
        "has_review_presence":  (rng.random(n) < 0.55).astype(int),
        "has_news_mention":     (rng.random(n) < 0.08).astype(int),
        "recently_registered":  (rng.random(n) < 0.10).astype(int),
        "expansion_signal":     (rng.random(n) < 0.15).astype(int),
    })
    df["intent_score"] = sum(df[col] * pts for col, pts in SIGNAL_POINTS.items())
    df["intent_score"] += rng.normal(20, 8, n).round().astype(int).clip(lower=0)
    return df


def main() -> None:
    df = synthetic_signals()
    print(f"Synthetic dataset: {len(df):,} records")

    present = {k: k for k in SIGNAL_POINTS if k in df.columns}

    rows = []
    for sig, col in present.items():
        pts = SIGNAL_POINTS[sig]
        n_signals = int(df[col].sum())
        rows.append({
            "signal": sig,
            "records_with_signal": n_signals,
            "pts_per_record": pts,
            "total_pts_contribution": n_signals * pts,
        })
    contrib = pd.DataFrame(rows).sort_values("total_pts_contribution", ascending=False)
    print("\nSignal contribution:")
    print(contrib.to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(contrib["signal"], contrib["records_with_signal"], color=GREEN_MID)
    axes[0].set_title("Reach: records carrying each signal")
    axes[0].set_ylabel("Count")
    axes[0].tick_params(axis="x", rotation=35)

    axes[1].bar(contrib["signal"], contrib["total_pts_contribution"], color=LIME, edgecolor=BLACK)
    axes[1].set_title("Impact: total intent points contributed")
    axes[1].set_ylabel("Points")
    axes[1].tick_params(axis="x", rotation=35)

    plt.tight_layout()
    plt.savefig(OUT / "signal_contribution.png", dpi=140)
    plt.close(fig)

    base_avg = df["intent_score"].mean()
    sim_rows = []
    for sig, col in present.items():
        pts = SIGNAL_POINTS[sig]
        simulated = df["intent_score"] - df[col] * pts
        sim_rows.append({"signal": sig, "score_loss_if_removed": base_avg - simulated.mean()})
    sim = pd.DataFrame(sim_rows).sort_values("score_loss_if_removed", ascending=False)
    print(f"\nBaseline avg intent score: {base_avg:.1f}")
    print("Score impact if signal removed:")
    print(sim.to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(sim["signal"], sim["score_loss_if_removed"], color="#DC2626", edgecolor=BLACK)
    ax.set_title("Avg intent-score loss if signal is removed")
    ax.set_ylabel("Score drop")
    ax.tick_params(axis="x", rotation=35)
    plt.tight_layout()
    plt.savefig(OUT / "signal_score_impact.png", dpi=140)
    plt.close(fig)

    print(f"\nCharts written to {OUT}")


if __name__ == "__main__":
    main()

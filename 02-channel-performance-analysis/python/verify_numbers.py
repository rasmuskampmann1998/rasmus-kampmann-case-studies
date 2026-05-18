"""
Canonical numbers for the Channel Performance case study.

Recomputes every quantitative claim that appears in README.md,
powerbi/dashboard-spec.md, and slides/deck-spec.md directly from the generated
star schema, and prints them in one block. The narrative files must quote these
values verbatim; CI / number-reviewer re-runs this and diffs.

Run from the case-study root:
    python python/verify_numbers.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

L = lambda n: pd.read_csv(DATA / f"{n}.csv", keep_default_na=False)
fd = L("fact_deals").astype({"is_won": int, "is_lost": int})
fm = L("fact_meetings")
ft = L("fact_touches")
for c in ("days_to_close", "days_from_first_touch"):
    fm[c] = pd.to_numeric(fm[c], errors="coerce")
fd["dialer_hours_attributed"] = pd.to_numeric(fd["dialer_hours_attributed"])
fd["mrr_usd"] = pd.to_numeric(fd["mrr_usd"])
fd = fd.astype({"is_churned": int})
fd["churned_mrr"] = pd.to_numeric(fd["churned_mrr"])
fd["retained_months"] = pd.to_numeric(fd["retained_months"], errors="coerce")
ch = L("dim_channel")
co = L("dim_company")
lr = L("dim_lost_reason")

D = fd.merge(ch, on="channel_key").merge(
    fm[["deal_key", "meeting_status", "days_to_close", "days_from_first_touch"]],
    on="deal_key")

CHANNEL_ORDER = ["Cold Calling", "LinkedIn Outbound", "Referral",
                 "Inbound Sales", "SEO", "Facebook Ads", "Instagram Ads",
                 "Cross-sell", "Upsell", "Re-bookings"]


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


print("=" * 70)
print("CHANNEL PERFORMANCE — CANONICAL NUMBERS (recomputed from data/)")
print("=" * 70)

# --- Top line -------------------------------------------------------------
n_deals = len(fd)
won_n = int(fd["is_won"].sum())
lost_n = int(fd["is_lost"].sum())
print("\n[Top line]")
print(f"  deals                  {n_deals:,}")
print(f"  won                    {won_n:,}  ({pct(won_n / n_deals)} blended)")
print(f"  lost                   {lost_n:,}")
print(f"  touches                {len(ft):,}")
print(f"  total won MRR          ${fd.loc[fd.is_won == 1, 'mrr_usd'].sum():,.0f}")
print(f"  avg MRR / won deal     ${fd.loc[fd.is_won == 1, 'mrr_usd'].mean():,.0f}")

# --- Channel performance table (the headline) -----------------------------
print("\n[Channel — win rate, volume, time-to-won, MRR/dialer-hr]")
g = D.groupby("channel_name").agg(
    deals=("deal_key", "count"),
    won=("is_won", "sum"),
    won_mrr=("mrr_usd", "sum"),
    dialer_hours=("dialer_hours_attributed", "sum"),
)
g["win_rate"] = g["won"] / g["deals"]
g["vol_share"] = g["deals"] / g["deals"].sum()
won_only = D[D["is_won"] == 1]
t2w = won_only.groupby("channel_name")["deal_age_days"].median()
print(f"  {'channel':<20}{'win':>7}{'vol':>8}{'t2w_med':>9}"
      f"{'wonMRR':>12}{'MRR/dlr-hr':>12}")
for cname in CHANNEL_ORDER:
    r = g.loc[cname]
    med = t2w.get(cname, float("nan"))
    mph = r["won_mrr"] / r["dialer_hours"] if r["dialer_hours"] > 0 else float("nan")
    mph_s = f"${mph:,.0f}" if mph == mph else "  n/a"
    print(f"  {cname:<20}{pct(r['win_rate']):>7}{pct(r['vol_share']):>8}"
          f"{med:>8.0f}d${r['won_mrr']:>10,.0f}{mph_s:>12}")

# --- Channel group rollup -------------------------------------------------
print("\n[Channel group — win rate, won MRR share]")
gg = D.groupby("channel_group").agg(
    deals=("deal_key", "count"), won=("is_won", "sum"),
    won_mrr=("mrr_usd", "sum"))
gg["win_rate"] = gg["won"] / gg["deals"]
tot_mrr = gg["won_mrr"].sum()
for grp, r in gg.sort_values("win_rate", ascending=False).iterrows():
    print(f"  {grp:<12} win {pct(r['win_rate']):>7}  "
          f"won MRR ${r['won_mrr']:,.0f} ({pct(r['won_mrr'] / tot_mrr)} of total)")

# --- Channel retention & NRR (the post-sale axis) -------------------------
# "Best channel" = wins fast AND at low acquisition cost AND whose customers
# STAY. Logo retention = share of won customers NOT churned within the 12-month
# observation window. NRR (gross-of-churn, no expansion modelled) = won MRR
# kept = (won_mrr - churned_mrr) / won_mrr. Small-n channels are flagged: with
# few won deals the realised retention is noisy and must be read directionally,
# not to the decimal (same hedging the win-rate table already applies).
print("\n[Channel retention & NRR — won deals, M12 window]")
rg = won_only.groupby("channel_name").agg(
    won=("deal_key", "count"),
    churned=("is_churned", "sum"),
    won_mrr=("mrr_usd", "sum"),
    churned_mrr=("churned_mrr", "sum"),
)
rg["retention"] = 1 - rg["churned"] / rg["won"]
rg["nrr"] = (rg["won_mrr"] - rg["churned_mrr"]) / rg["won_mrr"]
print(f"  {'channel':<20}{'M12 ret':>9}{'NRR':>8}{'won_n':>8}{'note':>16}")
for cname in CHANNEL_ORDER:
    if cname not in rg.index:
        continue
    r = rg.loc[cname]
    note = "small n — direc." if r["won"] < 50 else ""
    print(f"  {cname:<20}{pct(r['retention']):>9}{pct(r['nrr']):>8}"
          f"{int(r['won']):>8}{note:>16}")
blended_ret = 1 - won_only["is_churned"].sum() / len(won_only)
blended_nrr = ((won_only["mrr_usd"].sum() - won_only["churned_mrr"].sum())
               / won_only["mrr_usd"].sum())
print(f"  {'BLENDED':<20}{pct(blended_ret):>9}{pct(blended_nrr):>8}"
      f"{len(won_only):>8}")

# --- Dialer economics -----------------------------------------------------
print("\n[Dialer economics — dialer-motion channels only]")
dlr = D[D["is_dialer_motion"] == 1].copy()
dh = dlr["dialer_hours_attributed"].sum()
dmrr = dlr.loc[dlr.is_won == 1, "mrr_usd"].sum()
nondlr = D[D["is_dialer_motion"] == 0].copy()
print(f"  dialer hours total     {dh:,.0f} h")
print(f"  dialer won MRR         ${dmrr:,.0f}")
print(f"  dialer MRR / hour      ${dmrr / dh:,.0f}")
print(f"  dialer share of deals  {pct(len(dlr) / len(D))}")
print(f"  dialer share of wonMRR {pct(dmrr / fd.loc[fd.is_won == 1, 'mrr_usd'].sum())}")
print(f"  non-dialer won MRR     ${nondlr.loc[nondlr.is_won == 1, 'mrr_usd'].sum():,.0f}"
      f"  ({pct(len(nondlr) / len(D))} of deals)")

# --- Time-to-won percentiles by channel -----------------------------------
print("\n[Time-to-won (won deals) — median / p90 days, by channel]")
for cname in CHANNEL_ORDER:
    s = won_only[won_only["channel_name"] == cname]["deal_age_days"]
    if len(s):
        print(f"  {cname:<20} median {s.median():>4.0f}d   "
              f"p90 {s.quantile(0.9):>4.0f}d   (n={len(s):,})")

# --- Re-booking trap ------------------------------------------------------
reb = D[D["channel_name"] == "Re-bookings"]
reb_won = reb[reb.is_won == 1]
print("\n[Re-booking trap]")
print(f"  re-booking deals       {len(reb):,}")
print(f"  win rate               {pct(reb['is_won'].mean())}   (n={len(reb):,}, robust)")
print(f"  meeting cancel rate    {pct((reb['meeting_status'] == 'Cancelled').mean())}")
print(f"  dialer hours burned    {reb['dialer_hours_attributed'].sum():,.0f} h")
print(f"  won MRR returned       ${reb_won['mrr_usd'].sum():,.0f}")
# Retention corroborates the trap on a SECOND independent axis, but on only
# n={won} won deals — directional, not load-bearing. The trap stands on the
# robust win-rate axis (n above); retention is supporting evidence, hedged.
if len(reb_won):
    reb_ret = 1 - reb_won["is_churned"].mean()
    print(f"  M12 logo retention     {pct(reb_ret)}   "
          f"(n={len(reb_won)} won — DIRECTIONAL, small sample)")

# --- Loss mix -------------------------------------------------------------
dl = fd[fd["is_lost"] == 1].merge(lr, on="lost_reason_key")
canc_loss = int((dl["lost_reason"] == "Meeting No-Show / Cancelled").sum())
print("\n[Loss mix]")
print(f"  total losses           {lost_n:,}")
print(f"  cancellations          {canc_loss:,}  ({pct(canc_loss / lost_n)} of losses)")
cat = (dl["reason_category"].value_counts(normalize=True) * 100).round(1)
for k, v in cat.items():
    print(f"    {k:<14} {v:>5.1f}%")

# --- Channel x ICP (employee band) ----------------------------------------
print("\n[Channel x employee band — win rate, top channels]")
DI = D.merge(co[["company_key", "employee_band"]], on="company_key")
sweet = DI[DI["employee_band"] == "6-20"]
rest = DI[DI["employee_band"] != "6-20"]
print(f"  6-20 band win rate     {pct(sweet['is_won'].mean())}")
print(f"  other bands win rate   {pct(rest['is_won'].mean())}")

# --- Scorecard bands (channel allocation) ---------------------------------
# Additive, auditable: each channel scored on win rate, dialer cost,
# time-to-won, AND M12 logo retention (the post-sale axis added in Phase 8).
# Bands collapse to Scale / Maintain / Cap / Kill. Re-bookings now lands in
# Kill on TWO independent axes (it barely wins, and what it wins does not
# stay) — the retention factor strengthens, not invents, the verdict.
print("\n[Channel allocation scorecard — band coverage]")
SCALE = {"LinkedIn Outbound", "Referral", "Inbound Sales",
         "Cross-sell", "Upsell"}
MAINTAIN = {"Facebook Ads", "SEO", "Instagram Ads"}
CAP = {"Cold Calling"}
KILL = {"Re-bookings"}
total_won_mrr = fd.loc[fd.is_won == 1, "mrr_usd"].sum()
total_dh = fd["dialer_hours_attributed"].sum()
total_churned_mrr = fd.loc[fd.is_won == 1, "churned_mrr"].sum()
total_net_mrr = total_won_mrr - total_churned_mrr
for label, names in [("Scale", SCALE), ("Maintain", MAINTAIN),
                     ("Cap", CAP), ("Kill", KILL)]:
    sub = D[D["channel_name"].isin(names)]
    sub_won = sub[sub.is_won == 1]
    wmrr = sub_won["mrr_usd"].sum()
    net_mrr = wmrr - sub_won["churned_mrr"].sum()
    dh = sub["dialer_hours_attributed"].sum()
    ret = 1 - sub_won["is_churned"].mean() if len(sub_won) else float("nan")
    print(f"  {label:<9} {pct(len(sub) / len(D)):>6} of deals | "
          f"{pct(wmrr / total_won_mrr):>6} of won MRR | "
          f"{pct(net_mrr / total_net_mrr):>6} of net MRR | "
          f"M12 ret {pct(ret):>6} | "
          f"{pct(dh / total_dh):>6} of dialer hrs")

# --- Scorecard scoring rule (reproduces the deck Slide 10 bands) ----------
# Additive, monotone, auditable. Win rate + dialer cost separate the channels;
# time-to-won and M12 retention are corroborating bonuses (retention is
# NON-NEGATIVE by design so it cannot single-handedly flip a band — see the
# deck-spec rationale). This block IS the source of truth for the band table;
# the deck quotes these scores verbatim.
print("\n[Scorecard — per-channel score and band (the deck Slide 10 rule)]")
def _score(cn: str) -> int:
    sub = D[D["channel_name"] == cn]
    subw = sub[sub.is_won == 1]
    wr = sub["is_won"].mean()
    dhh = sub["dialer_hours_attributed"].sum()
    mph = (subw["mrr_usd"].sum() / dhh) if dhh > 0 else None
    t2 = subw["deal_age_days"].median()
    rt = 1 - subw["is_churned"].mean() if len(subw) else 0.0
    s = 0
    s += 50 if wr >= .50 else 30 if wr >= .25 else 12 if wr >= .10 else 4
    s += 30 if dhh == 0 else (12 if mph >= 15 else -8)
    s += 8 if t2 <= 10 else 3 if t2 <= 25 else 0
    s += 15 if rt >= .80 else 6 if rt >= .60 else 0
    return s
def _band(s: int) -> str:
    return ("Scale" if s >= 60 else "Maintain" if s >= 30
            else "Cap" if s >= 12 else "Kill")
for cn in CHANNEL_ORDER:
    sc = _score(cn)
    print(f"  {cn:<20} score {sc:>4}  -> {_band(sc)}")
print("=" * 70)

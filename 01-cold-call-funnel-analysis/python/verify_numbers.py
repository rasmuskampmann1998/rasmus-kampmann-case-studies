"""
Canonical numbers for case study #12.

Recomputes every quantitative claim that appears in README.md,
powerbi/dashboard-spec.md, and slides/deck-spec.md directly from the generated
star schema, and prints them in one block. The narrative files must quote these
values verbatim; CI/`number-reviewer` re-runs this and diffs.

Run from the case-study root:
    python python/verify_numbers.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

# keep_default_na=False so the literal accounting value "No System" is never
# coerced to NaN (and no other literal token is silently lost).
L = lambda n: pd.read_csv(DATA / f"{n}.csv", keep_default_na=False)
fc = L("fact_calls").astype({"is_connected": int, "is_meeting_booked": int})
fd = L("fact_deals").astype({"is_won": int, "is_lost": int})
fm = L("fact_meetings")
for c in ("days_to_close", "days_from_create"):
    fm[c] = pd.to_numeric(fm[c], errors="coerce")
co = L("dim_company")
rp = L("dim_rep")
lr = L("dim_lost_reason")

D = fd.merge(co, on="company_key").merge(
    fm[["deal_key", "meeting_status", "days_to_close", "days_from_create"]],
    on="deal_key")
held = D[D["meeting_status"] == "Held"]

ANTI_ICP = {"Consulting", "Marketing", "Transport"}
EMP_ORDER = ["1-5", "6-20", "21-50", "51-200", "201-500", "500+"]


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def rate(df: pd.DataFrame) -> float:
    return df["is_won"].mean() if len(df) else float("nan")


print("=" * 64)
print("CASE STUDY #12 — CANONICAL NUMBERS (recomputed from data/)")
print("=" * 64)

# --- Funnel waterfall -----------------------------------------------------
calls = len(fc)
connected = int(fc["is_connected"].sum())
booked = int(fc["is_meeting_booked"].sum())
held_n = int((fm["meeting_status"] == "Held").sum())
canc_n = int((fm["meeting_status"] == "Cancelled").sum())
won_n = int(fd["is_won"].sum())
lost_n = int(fd["is_lost"].sum())
print("\n[Funnel]")
print(f"  calls attempted        {calls:,}")
print(f"  calls connected        {connected:,}  ({pct(connected / calls)})")
print(f"  meetings booked        {booked:,}")
print(f"  meetings held          {held_n:,}")
print(f"  meetings cancelled     {canc_n:,}")
print(f"  deals won              {won_n:,}")
print(f"  meeting->won baseline  {pct(won_n / held_n)}")
print(f"  call->won overall      {pct(won_n / calls)}")

# --- Loss mix -------------------------------------------------------------
dl = fd[fd["is_lost"] == 1].merge(lr, on="lost_reason_key")
canc_loss = int((dl["lost_reason"] == "Meeting No-Show / Cancelled").sum())
print("\n[Loss mix]")
print(f"  total losses           {lost_n:,}")
print(f"  cancellations          {canc_loss:,}  ({pct(canc_loss / lost_n)} of losses)")
cat = (dl["reason_category"].value_counts(normalize=True) * 100).round(1)
for k, v in cat.items():
    print(f"    {k:<14} {v:>5.1f}%")

# --- Employee band: the primary ICP signal --------------------------------
print("\n[Employee band — held->won]  (PRIMARY ICP SIGNAL)")
eb = held.groupby("employee_band")["is_won"].agg(["count", "mean"])
for band in EMP_ORDER:
    if band in eb.index:
        r = eb.loc[band]
        print(f"  {band:<10} {pct(r['mean']):>7}  (n={int(r['count']):,})")
sweet = rate(held[held["employee_band"] == "6-20"])
rest = rate(held[held["employee_band"] != "6-20"])
print(f"  -> sweet spot 6-20: {pct(sweet)} vs everything else {pct(rest)} "
      f"({sweet / max(rest, 1e-9):.1f}x)")

# --- Accounting system: neutral descriptor (no signal expected) -----------
print("\n[Accounting system — held->won]  (neutral: every prospect has one)")
g = held.groupby("accounting_system")["is_won"].agg(["count", "mean"]).sort_values("mean")
for sysname, row in g.iterrows():
    print(f"  {sysname:<18} {pct(row['mean']):>7}  (n={int(row['count']):,})")
print(f"  -> spread {pct(g['mean'].min())}–{pct(g['mean'].max())} (flat = no signal)")

# --- Industry: the second ICP signal --------------------------------------
print("\n[Industry — held->won]")
gi = held.groupby("industry")["is_won"].agg(["count", "mean"]).sort_values("mean")
for ind, row in gi.iterrows():
    flag = "  <-- anti-ICP" if ind in ANTI_ICP else ""
    print(f"  {ind:<22} {pct(row['mean']):>7}  (n={int(row['count']):,}){flag}")
anti = held[held["industry"].isin(ANTI_ICP)]
print(f"  -> anti-ICP combined: {int(anti['is_won'].sum())} wins on {len(anti):,} held meetings")

# --- Company type ---------------------------------------------------------
print("\n[Company type — held->won]")
for ct, row in held.groupby("company_type")["is_won"].agg(["count", "mean"]).sort_values("mean", ascending=False).iterrows():
    print(f"  {ct:<20} {pct(row['mean']):>7}  (n={int(row['count']):,})")

# --- Rep skill ------------------------------------------------------------
print("\n[Rep skill — held->won]")
rh = held.merge(rp, on="rep_key").groupby(["rep_key", "rep_name"])["is_won"].agg(["count", "mean"])
rh = rh.sort_values("mean", ascending=False)
top = rh.iloc[0]
bot = rh.iloc[-1]
med = rh["mean"].median()
print(f"  top rep   {rh.index[0][1]:<18} {pct(top['mean'])}  (n={int(top['count'])})")
print(f"  2nd rep   {rh.index[1][1]:<18} {pct(rh.iloc[1]['mean'])}  (n={int(rh.iloc[1]['count'])})")
print(f"  median rep                       {pct(med)}")
print(f"  bottom rep {rh.index[-1][1]:<17} {pct(bot['mean'])}  (n={int(bot['count'])})")
print(f"  top/bottom ratio: {top['mean'] / max(bot['mean'], 1e-9):.0f}x")

# --- Re-booking ROI -------------------------------------------------------
reb = D[D["source_key"] == "SRC03"]
print("\n[Re-booking]")
print(f"  re-booked deals        {len(reb):,}")
print(f"  cancel again           {pct((reb['meeting_status'] == 'Cancelled').mean())}")
print(f"  close rate             {pct(reb['is_won'].mean())}")

# --- Velocity -------------------------------------------------------------
won_meet = fm.merge(fd[["deal_key", "is_won"]], on="deal_key")
wd = won_meet[won_meet["is_won"] == 1]["days_to_close"].dropna()
hd = won_meet[won_meet["meeting_status"] == "Held"]
print("\n[Velocity]")
print(f"  call->meeting median   {fm['days_from_create'].median():.0f} days")
print(f"  meeting->won median    {wd.median():.0f} days")
print(f"  meeting->won p90       {wd.quantile(0.9):.0f} days")
print(f"  held close <=30d       {pct(hd[hd['days_to_close'] <= 30]['is_won'].mean())}")
print(f"  held close >30d        {pct(hd[hd['days_to_close'] > 30]['is_won'].mean())}")

# --- Economics ------------------------------------------------------------
won = fd[fd["is_won"] == 1]
print("\n[Economics]")
print(f"  MRR won (USD)          ${won['mrr_usd'].sum():,.0f}")
print(f"  avg MRR / won deal     ${won['mrr_usd'].mean():,.0f}")
print("=" * 64)

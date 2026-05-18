"""
Build the fictionalized star schema for case study #12 (NorthStar Bookkeeping).

This is now a FULLY SELF-CONTAINED SYNTHETIC GENERATOR. It takes no private
input. The original portfolio build extracted from a private GTM repo whose
anonymized source CSVs are not redistributable, so this version generates a
designed synthetic funnel that reproduces the analytical narrative in README.md
end to end (cancellations dominate losses, a strong no-software segment lift,
anti-ICP industries that close ~zero, rep skill as the lever inside the meeting).

All numbers here are deliberately synthetic and round. They do not correspond to
any real client's results.

Determinism: every random draw is seeded so the output is byte-stable across runs.

Emits 10 CSVs to ../data/ matching the column contract in ../sql/schema.sql:
    dim_date, dim_company, dim_rep, dim_stage, dim_source, dim_lost_reason,
    dim_campaign, fact_calls, fact_meetings, fact_deals

Run from the case-study root:
    python python/build_dimensional_model.py
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from faker import Faker
except ImportError:  # pragma: no cover
    raise SystemExit("pip install faker") from None

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20260514
rng = np.random.default_rng(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

# Scale (kept close to the original shipped artefact).
N_COMPANIES = 102_476
N_CALLS = 102_007
N_REPS = 15

# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

# Productive industries plus the three anti-ICP industries the narrative names.
INDUSTRIES = [
    "Construction", "Healthcare", "Retail", "Manufacturing", "Hospitality",
    "Professional Services", "Other Services", "Other",
    "Consulting", "Marketing", "Transport",
]
INDUSTRY_W = [0.17, 0.10, 0.12, 0.08, 0.07, 0.16, 0.06, 0.05, 0.07, 0.04, 0.08]
ANTI_ICP = {"Consulting", "Marketing", "Transport"}
STRONG_ICP = {"Construction", "Healthcare", "Retail", "Manufacturing"}

# Every qualified prospect already runs an accounting system, so this is a
# neutral firmographic descriptor (vendor mix only) — it carries no close
# signal in the model. ICP is driven by employee band + industry instead.
ACCT_SYSTEMS = ["QuickBooks", "Xero", "FreshBooks", "NetSuite", "SAP Business One", "Sage"]
ACCT_W = [0.34, 0.24, 0.14, 0.12, 0.08, 0.08]

COMPANY_TYPES = ["LLC", "Sole Proprietorship", "Corporation", "Partnership"]
COMPANY_TYPE_W = [0.42, 0.30, 0.20, 0.08]

EMP_BANDS = ["1-5", "6-20", "21-50", "51-200", "201-500", "500+"]
EMP_W = [0.46, 0.28, 0.14, 0.07, 0.03, 0.02]
REV_BANDS = ["<$500K", "$500K-$2M", "$2M-$10M", "$10M-$50M", "$50M+"]
REV_W = [0.45, 0.30, 0.16, 0.07, 0.02]
REGIONS = ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "Northwest", "Southwest", "West"]
AGE_BANDS = ["0-2y", "3-5y", "6-10y", "11-20y", "20+y"]
AGE_W = [0.18, 0.28, 0.26, 0.18, 0.10]

STAGES = [
    ("S01", "01-Lead", 1, "Attempt"),
    ("S02", "02-Pending Meeting", 2, "Connect"),
    ("S03", "03-Meeting Held", 3, "Meeting"),
    ("S04", "03b-Meeting Cancelled", 3, "Meeting"),
    ("S05", "04-Follow-up Pending", 4, "Meeting"),
    ("S06", "04b-Follow-up Cancelled", 4, "Meeting"),
    ("S07", "05-Offer Validation", 5, "Negotiation"),
    ("S08", "06-Pending Final Accept", 6, "Negotiation"),
    ("S09", "07-Pending Onboarding", 7, "Close"),
    ("S10", "08-Won-Onboarded", 8, "Close"),
    ("S11", "09-Partner", 9, "Close"),
]

SOURCES = [
    ("SRC01", "Outbound Dialer", "Cold Call"),
    ("SRC02", "Sales Inbound", "Cold Call"),
    ("SRC03", "Re-booking", "Cold Call"),
    ("SRC04", "Referral", "Cold Call"),
    ("SRC05", "Cross-sell", "Cold Call"),
    ("SRC06", "Upsell", "Cold Call"),
]
SOURCE_KEYS = [s[0] for s in SOURCES]
SOURCE_W = [0.70, 0.10, 0.09, 0.05, 0.04, 0.02]

LOST_REASONS = [
    ("LR01", "Meeting No-Show / Cancelled", "No-response"),
    ("LR02", "No Response / Ghost", "No-response"),
    ("LR03", "Stale Lead", "No-response"),
    ("LR04", "Price / Budget", "Price"),
    ("LR05", "Timing - Not Ready", "Timing"),
    ("LR06", "Uses Competitor", "Competitor"),
    ("LR07", "Uses Competing Software", "Competitor"),
    ("LR08", "Has Internal Bookkeeper", "Fit"),
    ("LR09", "Not Qualified - No Registration", "Fit"),
    ("LR10", "Lack of Trust", "Fit"),
    ("LR11", "Meeting Booked Under Wrong Premise", "Fit"),
    ("LR12", "Hiring Process Outcome", "Other"),
    ("LR13", "Other", "Other"),
    ("LR14", "Unknown", "Unknown"),
]


# ---------------------------------------------------------------------------
# dim_date
# ---------------------------------------------------------------------------
print("[1/8] dim_date...")
D_MIN = date(2024, 1, 1)
D_MAX = date(2026, 12, 31)
date_range = pd.date_range(D_MIN, D_MAX, freq="D")
dim_date = pd.DataFrame({
    "date_key": [int(d.strftime("%Y%m%d")) for d in date_range],
    "date": [d.date().isoformat() for d in date_range],
    "year": date_range.year,
    "quarter": date_range.quarter,
    "month": date_range.month,
    "month_name": date_range.strftime("%B"),
    "week_of_year": date_range.isocalendar().week.values,
    "day_of_week": date_range.day_name(),
    "is_business_day": [d.weekday() < 5 for d in date_range],
})
dim_date.to_csv(OUT / "dim_date.csv", index=False)
BUSINESS_KEYS = dim_date.loc[dim_date["is_business_day"], "date_key"].to_numpy()


def rand_business_key(n: int) -> np.ndarray:
    return rng.choice(BUSINESS_KEYS, size=n)


def add_days_key(base_key: np.ndarray, days: np.ndarray) -> np.ndarray:
    """Shift a YYYYMMDD key by `days`, clamped to the dim_date range."""
    base = pd.to_datetime(base_key.astype(str), format="%Y%m%d")
    shifted = base + pd.to_timedelta(days, unit="D")
    lo = pd.Timestamp(D_MIN)
    hi = pd.Timestamp(D_MAX)
    shifted = shifted.where(shifted >= lo, lo).where(shifted <= hi, hi)
    return shifted.strftime("%Y%m%d").astype(int).to_numpy()


# ---------------------------------------------------------------------------
# dim_rep — 15 reps with a designed skill spread (the lever inside the meeting)
# ---------------------------------------------------------------------------
print("[2/8] dim_rep...")
TEAMS = ["Inside Sales A", "Inside Sales B", "Account Executives"]
TENURES = ["0-1y", "1-2y", "2-4y", "4+y"]
rep_fake = Faker("en_US")
rep_fake.seed_instance(SEED + 99)

# Per-rep additive skill term on the close log-odds. Two stars, a long
# competent middle, a weak bottom quartile. Index 0/1 are the stars.
REP_SKILL = np.array([
    3.05, 2.75,                          # R001, R002 — stars (60-76% close)
    0.85, 0.65, 0.45, 0.25, 0.10,        # solid middle (~ median 18-22%)
    0.00, -0.15, -0.30, -0.45,
    -0.95, -1.10, -1.25, -1.40,          # bottom quartile (~8%)
])
dim_rep = pd.DataFrame({
    "rep_key": [f"R{i + 1:03d}" for i in range(N_REPS)],
    "rep_name": [rep_fake.name() for _ in range(N_REPS)],
    "rep_team": [TEAMS[i % len(TEAMS)] for i in range(N_REPS)],
    "tenure_band": [TENURES[i % len(TENURES)] for i in range(N_REPS)],
})
dim_rep.to_csv(OUT / "dim_rep.csv", index=False)
REP_KEYS = dim_rep["rep_key"].to_numpy()
# Calls/meetings spread unevenly across reps (stars get fewer, harder leads
# would dilute the story, so keep volume roughly even with mild skew).
REP_VOL_W = np.array([0.9, 0.9, 1.1, 1.1, 1.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.95, 0.95, 0.95])
REP_VOL_W = REP_VOL_W / REP_VOL_W.sum()

# ---------------------------------------------------------------------------
# dim_stage / dim_source / dim_lost_reason / dim_campaign
# ---------------------------------------------------------------------------
print("[3/8] dim_stage, dim_source, dim_lost_reason, dim_campaign...")
pd.DataFrame(STAGES, columns=["stage_key", "stage_name", "stage_order", "funnel_step"]) \
    .to_csv(OUT / "dim_stage.csv", index=False)
pd.DataFrame(SOURCES, columns=["source_key", "source_name", "channel"]) \
    .to_csv(OUT / "dim_source.csv", index=False)
dim_lost_reason = pd.DataFrame(LOST_REASONS, columns=["lost_reason_key", "lost_reason", "reason_category"])
dim_lost_reason.to_csv(OUT / "dim_lost_reason.csv", index=False)

camp_fake = Faker("en_US")
camp_fake.seed_instance(SEED + 7)
N_CAMP = 11
camp_seg = ["SMB", "Mid-Market", "Enterprise"]
dim_campaign = pd.DataFrame({
    "campaign_key": [f"CMP{i + 1:03d}" for i in range(N_CAMP)],
    "campaign_name": [f"{camp_fake.bs().title()} Campaign" for _ in range(N_CAMP)],
    "segment": [camp_seg[i % len(camp_seg)] for i in range(N_CAMP)],
    "launch_date": [(D_MIN + timedelta(days=int(rng.integers(0, 700)))).isoformat() for _ in range(N_CAMP)],
})
dim_campaign.to_csv(OUT / "dim_campaign.csv", index=False)

# ---------------------------------------------------------------------------
# dim_company
# ---------------------------------------------------------------------------
print("[4/8] dim_company...")
comp_fake = Faker("en_US")
comp_fake.seed_instance(SEED + 3)

industry = rng.choice(INDUSTRIES, size=N_COMPANIES, p=np.array(INDUSTRY_W) / sum(INDUSTRY_W))
acct = rng.choice(ACCT_SYSTEMS, size=N_COMPANIES, p=np.array(ACCT_W) / sum(ACCT_W))
ctype = rng.choice(COMPANY_TYPES, size=N_COMPANIES, p=np.array(COMPANY_TYPE_W) / sum(COMPANY_TYPE_W))
emp = rng.choice(EMP_BANDS, size=N_COMPANIES, p=np.array(EMP_W) / sum(EMP_W))
revb = rng.choice(REV_BANDS, size=N_COMPANIES, p=np.array(REV_W) / sum(REV_W))
region = rng.choice(REGIONS, size=N_COMPANIES)
ageb = rng.choice(AGE_BANDS, size=N_COMPANIES, p=np.array(AGE_W) / sum(AGE_W))

suffixes = np.array(["Inc.", "LLC", "Co.", "Group", "Holdings", "Partners"])
words = np.array([comp_fake.last_name() for _ in range(4000)])
lastn = np.array([comp_fake.last_name() for _ in range(4000)])
dim_company = pd.DataFrame({
    "company_key": [f"C{i:07d}" for i in range(N_COMPANIES)],
    "company_name": [
        f"{words[i % 4000]} {lastn[(i * 7) % 4000]} {suffixes[i % 6]}"
        for i in range(N_COMPANIES)
    ],
    "industry": industry,
    "employee_band": emp,
    "revenue_band_usd": revb,
    "region": region,
    "accounting_system": acct,
    "company_type": ctype,
    "company_age_band": ageb,
})
dim_company.to_csv(OUT / "dim_company.csv", index=False)


# ---------------------------------------------------------------------------
# Direct close-probability model — firmographic ICP
# ---------------------------------------------------------------------------
# Every prospect already runs an accounting system, so accounting vendor is a
# neutral descriptor and carries NO close signal. The ICP is firmographic:
#   - employee band is the primary signal (a clear mid-market sweet spot:
#     6-20 employees closes best; sole operators churn, big firms have an
#     incumbent finance function)
#   - industry is the second signal (anti-ICP industries close ~0; a strong
#     set converts above baseline)
#   - rep skill is the dominant coachable lever inside the meeting
#   - prior cancels and re-bookings depress close odds
# A No-System / accounting anchor is deliberately absent. Two independent 1-D
# solves (employee sweet-spot multiplier; global blend scale) keep the
# headline numbers on target every run.

# Employee-band anchor probability — the primary ICP story.
EMP_ANCHOR = {
    "1-5":     0.08,   # sole operators / micro — churn, price-sensitive
    "6-20":    0.34,   # the sweet spot
    "21-50":   0.22,
    "51-200":  0.12,
    "201-500": 0.05,   # incumbent finance team
    "500+":    0.03,
}
SWEET_BAND = "6-20"

# Rep tilt: map the designed REP_SKILL spread to a multiplier so the top reps
# clearly dominate (the coachable-lever story) and the bottom quartile lags.
_rs = REP_SKILL - REP_SKILL[5]            # center on a mid rep
REP_MULT = np.clip(np.exp(0.62 * _rs), 0.18, 4.2)


def close_prob(idx: np.ndarray, rep_key: np.ndarray, prior_cancels: np.ndarray,
                k: float, sweet_mult: float = 1.0) -> np.ndarray:
    """Per-held-meeting win probability.

    `sweet_mult` independently scales the 6-20 employee sweet spot so it lands
    on its target rate; `k` scales everything else so the blended held->won
    rate hits ~13%. Anti-ICP industries are pinned near zero.
    """
    eb = dim_company["employee_band"].to_numpy()[idx]
    p = np.full(len(idx), EMP_ANCHOR["1-5"])
    for band, anchor in EMP_ANCHOR.items():
        p = np.where(eb == band, anchor, p)
    is_sweet = (eb == SWEET_BAND)

    rep_pos = np.searchsorted(REP_KEYS, rep_key)
    p = p * REP_MULT[rep_pos]

    ind = dim_company["industry"].to_numpy()[idx]
    p = np.where(np.isin(ind, list(STRONG_ICP)), p * 1.25, p)

    ct = dim_company["company_type"].to_numpy()[idx]
    p = np.where(ct == "LLC", p * 1.10, p)
    p = np.where(ct == "Corporation", p * 1.05, p)

    p = np.where(prior_cancels == 1, p * 0.85, p)
    p = np.where(prior_cancels >= 2, p * 0.55, p)
    # Re-booked (held) meetings still close worse than a first meeting.
    p = np.where(h_reb, p * 0.62, p)

    # Sweet-spot band scaled independently of the blend constraint so the
    # primary ICP lift is preserved; everything else scaled by k.
    p = np.where(is_sweet, p * sweet_mult, p * k)
    # Anti-ICP industries close ~0 regardless of everything else.
    p = np.where(np.isin(ind, list(ANTI_ICP)), 0.002, p)
    return np.clip(p, 0.0, 0.985)


# ---------------------------------------------------------------------------
# fact_calls
# ---------------------------------------------------------------------------
print("[5/8] fact_calls...")
call_company = rng.integers(0, N_COMPANIES, size=N_CALLS)
call_rep = rng.choice(REP_KEYS, size=N_CALLS, p=REP_VOL_W)

CALL_OUTCOMES = ["Answered", "No Answer", "Busy", "Voicemail", "Wrong Number",
                 "No Callback", "Meeting Booked", "Re-booking", "Wrap-up",
                 "Drop-off", "Dead Lead", "Network Error"]
CALL_OUT_W = np.array([0.20, 0.30, 0.07, 0.13, 0.03, 0.05, 0.055, 0.015,
                       0.03, 0.05, 0.03, 0.02])
call_outcome = rng.choice(CALL_OUTCOMES, size=N_CALLS, p=CALL_OUT_W / CALL_OUT_W.sum())
is_connected = np.isin(call_outcome, ["Answered", "Meeting Booked", "Re-booking", "Wrap-up"]).astype(int)
is_meeting_booked = (call_outcome == "Meeting Booked").astype(int)

fact_calls = pd.DataFrame({
    "call_key": [f"CALL{i + 1:08d}" for i in range(N_CALLS)],
    "company_key": [f"C{c:07d}" for c in call_company],
    "rep_key": call_rep,
    "call_date_key": rand_business_key(N_CALLS),
    "call_outcome": call_outcome,
    "attempts_count": rng.integers(1, 9, size=N_CALLS),
    "call_duration_sec": np.where(
        is_connected == 1, rng.integers(30, 720, size=N_CALLS),
        rng.integers(0, 30, size=N_CALLS)),
    "is_connected": is_connected,
    "is_meeting_booked": is_meeting_booked,
})
fact_calls.to_csv(OUT / "fact_calls.csv", index=False)

# ---------------------------------------------------------------------------
# fact_deals + fact_meetings
# ---------------------------------------------------------------------------
print("[6/8] fact_deals + fact_meetings...")
# One deal per booked-meeting opportunity, plus a few inbound/referral deals.
booked_idx = np.where(is_meeting_booked == 1)[0]
N_DEALS = 4691
# Sample deal opportunities from booked meetings (with replacement if short).
sel = rng.choice(booked_idx, size=N_DEALS, replace=len(booked_idx) < N_DEALS)
deal_company = call_company[sel]
deal_rep = call_rep[sel]
created_key = rand_business_key(N_DEALS)

source_key = rng.choice(SOURCE_KEYS, size=N_DEALS, p=np.array(SOURCE_W) / sum(SOURCE_W))

# Prior cancel history (drives the cancel-penalty + re-booking ROI story).
prior_cancels = rng.choice([0, 1, 2, 3], size=N_DEALS, p=[0.62, 0.22, 0.11, 0.05])
is_rebooking = (source_key == "SRC03")

# Meeting held vs cancelled. Re-bookings cancel ~55%; base cancel ~30%,
# climbing with prior cancels. Cancelled meetings never win.
p_cancel = 0.31 + 0.11 * prior_cancels
p_cancel = np.where(is_rebooking, np.maximum(p_cancel, 0.55), p_cancel)
p_cancel = np.clip(p_cancel, 0, 0.92)
cancelled = rng.random(N_DEALS) < p_cancel

held = ~cancelled
held_idx = np.where(held)[0]
h_company = deal_company[held_idx]
h_rep = deal_rep[held_idx]
h_pc = prior_cancels[held_idx]
h_reb = is_rebooking[held_idx]


# Fixed draw used during calibration so we solve against the *realised* blended
# rate; the same draw produces the data, so the calibrated scale holds exactly.
_calib_u = np.random.default_rng(SEED + 500).random(len(held_idx))


_eb_held = dim_company["employee_band"].to_numpy()[h_company]
_sweet_mask = (_eb_held == SWEET_BAND)


def _bisect(fn, target, lo, hi, iters=44):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# Two independent solves keep the headline numbers reproducible:
#   sweet_mult -> 6-20 employee band held->won ~38% (the primary ICP lift)
#   k          -> overall blended held->won ~13% (the headline baseline)
# The rep-skill spread is then whatever the designed REP_MULT produces under
# those constraints; the README reports the realised top/bottom rep rates.
K, SWEET_MULT = 0.20, 1.0
for _ in range(4):
    SWEET_MULT = _bisect(
        lambda sm: (close_prob(h_company, h_rep, h_pc, K, sm) > _calib_u)[_sweet_mask].mean(),
        0.38, 0.05, 8.0)
    K = _bisect(
        lambda k: (close_prob(h_company, h_rep, h_pc, k, SWEET_MULT) > _calib_u).mean(),
        0.13, 0.02, 6.0)
_p = close_prob(h_company, h_rep, h_pc, K, SWEET_MULT)
print(f"        calibrated k={K:.4f} sweet_mult={SWEET_MULT:.4f} "
      f"blended={(_p > _calib_u).mean():.4f} "
      f"sweet_6_20={((_p > _calib_u)[_sweet_mask]).mean():.4f}")

# Produce the data with the SAME draw the calibration solved against.
won_held = _p > _calib_u
won = np.zeros(N_DEALS, dtype=bool)
won[held_idx] = won_held

# Slow deals (>30 days meeting->close) close at half rate: model close delay,
# then knock out a share of slow would-be wins to halve their rate.
meeting_offset = rng.integers(0, 2, size=N_DEALS)            # call -> meeting 0-1d
close_delay = rng.gamma(shape=2.2, scale=6.0, size=N_DEALS)  # meeting -> close
close_delay = np.round(close_delay).astype(int)
slow = close_delay > 30
slow_kill = won & slow & (rng.random(N_DEALS) < 0.5)
won = won & ~slow_kill

status = np.where(won, "Won", "Lost")
is_won = won.astype(int)
is_lost = (~won).astype(int)

# Lost-reason assignment: cancelled meetings -> No-Show/Cancelled (this makes
# cancellations ~43% of all losses since cancels dominate the lost pool).
lr_key = np.empty(N_DEALS, dtype=object)
lost_mask = ~won
lr_key[cancelled & lost_mask] = "LR01"
other_lost = lost_mask & ~cancelled
OTHER_LR = ["LR02", "LR03", "LR04", "LR05", "LR06", "LR07", "LR08", "LR09",
            "LR10", "LR11", "LR12", "LR13", "LR14"]
OTHER_LR_W = np.array([0.16, 0.10, 0.10, 0.13, 0.07, 0.06, 0.09, 0.05, 0.05,
                       0.04, 0.03, 0.07, 0.05])
n_other = int(other_lost.sum())
lr_key[other_lost] = rng.choice(OTHER_LR, size=n_other, p=OTHER_LR_W / OTHER_LR_W.sum())
lr_key[won] = "LR14"  # not used in loss analysis (filtered by is_lost)

# Stage from outcome.
stage_key = np.where(
    won, rng.choice(["S10", "S11"], size=N_DEALS, p=[0.85, 0.15]),
    np.where(cancelled,
             rng.choice(["S04", "S06"], size=N_DEALS, p=[0.8, 0.2]),
             rng.choice(["S02", "S05", "S07", "S08"], size=N_DEALS, p=[0.4, 0.3, 0.2, 0.1])))

won_key = np.where(won, add_days_key(created_key, meeting_offset + close_delay), 0)
lost_key = np.where(~won, add_days_key(created_key, meeting_offset + close_delay), 0)
deal_age = np.where(won, meeting_offset + close_delay,
                    np.where(~won, meeting_offset + close_delay, np.nan)).astype(float)

# MRR/TCV only meaningful for won; lost deals get 0.
mrr = np.where(won, np.round(rng.uniform(180, 1400, size=N_DEALS), 2), 0.0)
tcv = np.where(won, np.round(mrr * rng.uniform(10, 16, size=N_DEALS), 2), 0.0)

fact_deals = pd.DataFrame({
    "deal_key": [f"D{i + 1:07d}" for i in range(N_DEALS)],
    "company_key": [f"C{c:07d}" for c in deal_company],
    "rep_key": deal_rep,
    "source_key": source_key,
    "stage_key": stage_key,
    "lost_reason_key": lr_key,
    "created_date_key": created_key,
    "won_date_key": won_key,
    "lost_date_key": lost_key,
    "mrr_usd": mrr,
    "tcv_usd": tcv,
    "deal_age_days": deal_age,
    "is_won": is_won,
    "is_lost": is_lost,
})
fact_deals.to_csv(OUT / "fact_deals.csv", index=False)

# fact_meetings — one per deal (every deal came from a booked meeting).
meeting_status = np.where(cancelled, "Cancelled", "Held")
no_show = cancelled.astype(int)
days_from_create = meeting_offset.astype(float)
days_to_close = np.where(held, (close_delay).astype(float), np.nan)

fact_meetings = pd.DataFrame({
    "meeting_key": [f"M{i + 1:07d}" for i in range(N_DEALS)],
    "deal_key": fact_deals["deal_key"],
    "company_key": fact_deals["company_key"],
    "rep_key": deal_rep,
    "meeting_date_key": add_days_key(created_key, meeting_offset),
    "meeting_status": meeting_status,
    "no_show_flag": no_show,
    "days_from_create": days_from_create,
    "days_to_close": days_to_close,
})
fact_meetings.to_csv(OUT / "fact_meetings.csv", index=False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("[7/8] Output:")
for f in sorted(OUT.glob("*.csv")):
    print(f"   {f.name:24s} {f.stat().st_size / 1024:>10,.1f} KB")

held_n = int((meeting_status == "Held").sum())
won_n = int(is_won.sum())
lost_n = int(is_lost.sum())
canc_losses = int(((lr_key == "LR01") & (is_lost == 1)).sum())
print("[8/8] Headline check:")
print(f"   meetings held         {held_n:,}")
print(f"   won                   {won_n:,}  ({100 * won_n / held_n:.1f}% of held)")
print(f"   cancel share of loss  {100 * canc_losses / lost_n:.1f}%")

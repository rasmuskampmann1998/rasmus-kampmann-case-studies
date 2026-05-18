"""
Build the fictionalized star schema for the Channel Performance case study.

This is a FULLY SELF-CONTAINED SYNTHETIC GENERATOR. It takes no private input.
The original analysis ran on a private CRM export whose anonymized CSVs
are not redistributable, so this version generates a designed synthetic deal
population that reproduces the analytical narrative in README.md end to end:

  - cold calling is the highest-volume channel but the lowest win rate and the
    slowest to close (the dilution trap)
  - LinkedIn outbound and referral close fast and high, but are under-scaled
  - cross-sell / upsell (existing-base expansion) close highest and fastest
  - re-bookings look like a channel but behave like churn (lowest win rate)
  - dialer hours are spent disproportionately on the channels that return least

All numbers here are deliberately synthetic and round. They do not correspond
to any real client's results.

Determinism: every random draw is seeded so the output is byte-stable across
runs.

Emits 10 CSVs to ../data/ matching the column contract in ../sql/schema.sql:
    dim_date, dim_channel, dim_campaign, dim_company, dim_rep, dim_stage,
    dim_lost_reason, fact_touches, fact_deals, fact_meetings

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

SEED = 20260515
rng = np.random.default_rng(SEED)
Faker.seed(SEED)

# Scale.
N_COMPANIES = 60_000
N_TOUCHES = 90_000
N_DEALS = 7_300
N_REPS = 15

# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

# Channel is the PRIMARY designed signal. Each row:
#   (key, name, group, is_dialer_motion, cost_model,
#    deal_share, win_anchor, t2w_scale, m12_retention)
# deal_share    — share of all deals created through this channel
# win_anchor    — designed channel win rate (before firmographic tilt + calib)
# t2w_scale     — gamma scale for days-from-first-touch-to-won (median ~ 1.7*scale)
# m12_retention — designed share of WON customers still active at month 12.
#                 This is the post-sale axis: a channel can win deals that then
#                 cancel. Re-bookings is lowest by design (0.38) — the "trap" is
#                 now proven on TWO independent axes (it wins little AND what it
#                 wins does not stay), not relabelled from a low win rate.
CHANNELS = [
    ("CH01", "Cold Calling",      "Outbound",  1, "per-dial", 0.605, 0.086, 13.0, 0.55),
    ("CH02", "LinkedIn Outbound", "Outbound",  0, "per-lead", 0.060, 0.640,  6.2, 0.80),
    ("CH03", "Referral",          "Referral",  0, "zero",     0.040, 0.980,  4.5, 0.88),
    ("CH04", "Inbound Sales",     "Inbound",   0, "per-lead", 0.060, 0.760, 10.0, 0.80),
    ("CH05", "SEO",               "Inbound",   0, "zero",     0.046, 0.099, 16.0, 0.68),
    ("CH06", "Facebook Ads",      "Paid",      0, "CPM",      0.052, 0.165, 16.0, 0.68),
    ("CH07", "Instagram Ads",     "Paid",      0, "CPM",      0.040, 0.074, 10.0, 0.68),
    ("CH08", "Cross-sell",        "Expansion", 0, "zero",     0.035, 0.985,  3.5, 0.92),
    ("CH09", "Upsell",            "Expansion", 0, "zero",     0.022, 0.940,  3.0, 0.92),
    ("CH10", "Re-bookings",       "Outbound",  1, "per-dial", 0.040, 0.040, 15.0, 0.38),
]
CHANNEL_KEYS = np.array([c[0] for c in CHANNELS])
CHANNEL_SHARE = np.array([c[5] for c in CHANNELS])
CHANNEL_SHARE = CHANNEL_SHARE / CHANNEL_SHARE.sum()
WIN_ANCHOR = {c[0]: c[6] for c in CHANNELS}
T2W_SCALE = {c[0]: c[7] for c in CHANNELS}
M12_RETENTION = {c[0]: c[8] for c in CHANNELS}
IS_DIALER = {c[0]: c[3] for c in CHANNELS}

INDUSTRIES = [
    "Construction", "Healthcare", "Retail", "Manufacturing", "Hospitality",
    "Professional Services", "Other Services", "Other",
    "Consulting", "Marketing", "Transport",
]
INDUSTRY_W = [0.17, 0.10, 0.12, 0.08, 0.07, 0.16, 0.06, 0.05, 0.07, 0.04, 0.08]
ANTI_ICP = {"Consulting", "Marketing", "Transport"}
STRONG_ICP = {"Construction", "Healthcare", "Retail", "Manufacturing"}

COMPANY_FORMS = ["LLC", "Sole Proprietorship", "Corporation", "Partnership"]
COMPANY_FORM_W = [0.42, 0.30, 0.20, 0.08]

EMP_BANDS = ["1-5", "6-20", "21-50", "51-200", "201-500", "500+"]
EMP_W = [0.46, 0.28, 0.14, 0.07, 0.03, 0.02]
REV_BANDS = ["<$500K", "$500K-$2M", "$2M-$10M", "$10M-$50M", "$50M+"]
REV_W = [0.45, 0.30, 0.16, 0.07, 0.02]
REGIONS = ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "Northwest", "Southwest", "West"]
AGE_BANDS = ["0-2y", "3-5y", "6-10y", "11-20y", "20+y"]
AGE_W = [0.18, 0.28, 0.26, 0.18, 0.10]

STAGES = [
    ("S01", "01-Lead", 1, "Lead"),
    ("S02", "02-Meeting Booked", 2, "Meeting"),
    ("S03", "03-Meeting Held", 3, "Meeting"),
    ("S04", "03b-Meeting Cancelled", 3, "Meeting"),
    ("S05", "04-Negotiation", 4, "Negotiation"),
    ("S06", "05-Pending Onboarding", 5, "Close"),
    ("S07", "06-Won-Onboarded", 6, "Close"),
    ("S08", "07-Partner", 7, "Close"),
    ("S09", "04b-Negotiation Stalled", 4, "Negotiation"),
]
WON_STAGES = ["S07", "S08"]

LOST_REASONS = [
    ("LR01", "Meeting No-Show / Cancelled", "No-response"),
    ("LR02", "No Response / Ghost", "No-response"),
    ("LR03", "Stale Lead", "No-response"),
    ("LR04", "Price / Budget", "Price"),
    ("LR05", "Timing - Not Ready", "Timing"),
    ("LR06", "Uses Competitor", "Competitor"),
    ("LR07", "Uses Competing Software", "Competitor"),
    ("LR08", "Has Internal Bookkeeper", "Fit"),
    ("LR09", "Not Qualified", "Fit"),
    ("LR10", "Lack of Trust", "Fit"),
    ("LR11", "Booked Under Wrong Premise", "Fit"),
    ("LR12", "Hiring Process Outcome", "Other"),
    ("LR13", "Other", "Other"),
    ("LR14", "Unknown", "Unknown"),
]

# ---------------------------------------------------------------------------
# dim_date
# ---------------------------------------------------------------------------
print("[1/9] dim_date...")
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
# dim_channel
# ---------------------------------------------------------------------------
print("[2/9] dim_channel...")
dim_channel = pd.DataFrame(
    [(k, n, g, d, cm) for (k, n, g, d, cm, *_rest) in CHANNELS],
    columns=["channel_key", "channel_name", "channel_group",
             "is_dialer_motion", "cost_model"],
)
dim_channel.to_csv(OUT / "dim_channel.csv", index=False)

# ---------------------------------------------------------------------------
# dim_rep — 15 reps with a mild designed skill spread (secondary lever)
# ---------------------------------------------------------------------------
print("[3/9] dim_rep...")
TEAMS = ["Inside Sales A", "Inside Sales B", "Account Executives"]
TENURES = ["0-1y", "1-2y", "2-4y", "4+y"]
rep_fake = Faker("en_US")
rep_fake.seed_instance(SEED + 99)

# Channel is the dominant axis; rep skill is a small additive tilt so the
# leaderboard has spread without overpowering the channel story.
REP_SKILL = np.array([
    0.85, 0.70, 0.55, 0.40, 0.30, 0.20, 0.10,
    0.00, -0.10, -0.20, -0.30,
    -0.45, -0.55, -0.65, -0.80,
])
dim_rep = pd.DataFrame({
    "rep_key": [f"R{i + 1:03d}" for i in range(N_REPS)],
    "rep_name": [rep_fake.name() for _ in range(N_REPS)],
    "rep_team": [TEAMS[i % len(TEAMS)] for i in range(N_REPS)],
    "tenure_band": [TENURES[i % len(TENURES)] for i in range(N_REPS)],
})
dim_rep.to_csv(OUT / "dim_rep.csv", index=False)
REP_KEYS = dim_rep["rep_key"].to_numpy()
REP_VOL_W = np.full(N_REPS, 1.0)
REP_VOL_W = REP_VOL_W / REP_VOL_W.sum()
_rs = REP_SKILL - REP_SKILL[7]
REP_MULT = np.clip(np.exp(0.38 * _rs), 0.5, 2.0)

# ---------------------------------------------------------------------------
# dim_stage / dim_lost_reason / dim_campaign
# ---------------------------------------------------------------------------
print("[4/9] dim_stage, dim_lost_reason, dim_campaign...")
pd.DataFrame(STAGES, columns=["stage_key", "stage_name", "stage_order", "funnel_step"]) \
    .to_csv(OUT / "dim_stage.csv", index=False)
pd.DataFrame(LOST_REASONS, columns=["lost_reason_key", "lost_reason", "reason_category"]) \
    .to_csv(OUT / "dim_lost_reason.csv", index=False)

# Campaigns belong to the two paid channels only (the rest carry no campaign).
camp_fake = Faker("en_US")
camp_fake.seed_instance(SEED + 7)
PAID_CHANNELS = ["CH06", "CH07"]
camp_seg = ["SMB", "Mid-Market", "Enterprise"]
N_CAMP = 10
camp_chan = [PAID_CHANNELS[i % 2] for i in range(N_CAMP)]
dim_campaign = pd.DataFrame({
    "campaign_key": [f"CMP{i + 1:03d}" for i in range(N_CAMP)],
    "campaign_name": [f"{camp_fake.bs().title()} Campaign" for _ in range(N_CAMP)],
    "channel_key": camp_chan,
    "segment": [camp_seg[i % len(camp_seg)] for i in range(N_CAMP)],
    "launch_date": [(D_MIN + timedelta(days=int(rng.integers(0, 700)))).isoformat()
                    for _ in range(N_CAMP)],
})
dim_campaign.to_csv(OUT / "dim_campaign.csv", index=False)
CAMP_BY_CHANNEL = {
    "CH06": dim_campaign.loc[dim_campaign["channel_key"] == "CH06", "campaign_key"].to_numpy(),
    "CH07": dim_campaign.loc[dim_campaign["channel_key"] == "CH07", "campaign_key"].to_numpy(),
}

# ---------------------------------------------------------------------------
# dim_company
# ---------------------------------------------------------------------------
print("[5/9] dim_company...")
comp_fake = Faker("en_US")
comp_fake.seed_instance(SEED + 3)

industry = rng.choice(INDUSTRIES, size=N_COMPANIES, p=np.array(INDUSTRY_W) / sum(INDUSTRY_W))
form = rng.choice(COMPANY_FORMS, size=N_COMPANIES, p=np.array(COMPANY_FORM_W) / sum(COMPANY_FORM_W))
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
    "company_form": form,
    "company_age_band": ageb,
})
dim_company.to_csv(OUT / "dim_company.csv", index=False)


# ---------------------------------------------------------------------------
# Channel-driven close-probability model
# ---------------------------------------------------------------------------
# Channel is the dominant signal: each channel has a designed win anchor (the
# table at the top). Firmographic ICP (employee band + industry) is a SECONDARY
# tilt so channel stays the headline axis. Anti-ICP industries still close ~0.
# One global blend scale k is calibrated so the overall blended win rate lands
# on target; per-channel anchors then reproduce on every run.

EMP_TILT = {
    "1-5": 0.85, "6-20": 1.18, "21-50": 1.10,
    "51-200": 0.95, "201-500": 0.85, "500+": 0.80,
}


def close_prob(chan: np.ndarray, comp_idx: np.ndarray, rep_key: np.ndarray,
                k: float = 1.0) -> np.ndarray:
    """Per-deal win probability, channel-anchored with a firmographic tilt.

    `k` is a single global multiplier solved by bisection so each channel's
    REALISED win rate lands on its designed anchor after the firmographic
    tilt + rep spread drift it slightly. It scales every channel by the same
    factor, so the channel ordering and relative spread the narrative reports
    are exactly preserved; only the small tilt drift is corrected.
    """
    p = np.array([WIN_ANCHOR[c] for c in chan], dtype=float)

    eb = dim_company["employee_band"].to_numpy()[comp_idx]
    tilt = np.ones(len(comp_idx))
    for band, t in EMP_TILT.items():
        tilt = np.where(eb == band, t, tilt)
    p = p * tilt

    ind = dim_company["industry"].to_numpy()[comp_idx]
    p = np.where(np.isin(ind, list(STRONG_ICP)), p * 1.08, p)

    rep_pos = np.searchsorted(REP_KEYS, rep_key)
    p = p * REP_MULT[rep_pos]

    # Anti-ICP industries close ~0 regardless of channel.
    p = np.where(np.isin(ind, list(ANTI_ICP)), p * 0.06, p)

    # Global scale: a near-pure multiplier so per-channel anchors are preserved
    # (it does NOT pull channels toward a common mean). k is calibrated only to
    # absorb the firmographic-tilt drift so the blended rate lands on target;
    # the channel ordering and spread the narrative reports are intact.
    p = p * k
    return np.clip(p, 0.0, 0.985)


# ---------------------------------------------------------------------------
# fact_deals
# ---------------------------------------------------------------------------
print("[6/9] fact_deals...")
deal_channel = rng.choice(CHANNEL_KEYS, size=N_DEALS, p=CHANNEL_SHARE)
deal_company = rng.integers(0, N_COMPANIES, size=N_DEALS)
deal_rep = rng.choice(REP_KEYS, size=N_DEALS, p=REP_VOL_W)
created_key = rand_business_key(N_DEALS)

# Campaign only for paid-channel deals; everything else has no campaign.
campaign_key = np.full(N_DEALS, "", dtype=object)
for ch in ("CH06", "CH07"):
    m = deal_channel == ch
    campaign_key[m] = rng.choice(CAMP_BY_CHANNEL[ch], size=int(m.sum()))

# Fixed calibration draw: solve against the realised blended rate so the
# calibrated scale holds exactly when the same draw produces the data.
_calib_u = np.random.default_rng(SEED + 500).random(N_DEALS)


def _bisect(fn, target, lo, hi, iters=46):
    for _ in range(iters):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# One solve: pin Cold Calling (the highest-volume channel and the one the
# narrative anchors at ~8.6%) to its designed rate. Because k is a uniform
# multiplier, every other channel keeps its relative position; the blended
# win rate is then a derived output, not an imposed constraint.
_cc_mask = deal_channel == "CH01"
K = _bisect(
    lambda k: (close_prob(deal_channel, deal_company, deal_rep, k) > _calib_u)[_cc_mask].mean(),
    0.086, 0.05, 8.0)
_p = close_prob(deal_channel, deal_company, deal_rep, K)
won = _p > _calib_u
print(f"        calibrated k={K:.4f} cold_call={(won)[_cc_mask].mean():.4f} "
      f"blended_win={(won).mean():.4f}")

is_won = won.astype(int)
is_lost = (~won).astype(int)

# Time from first touch to won/closed, per-channel gamma scale (fast for
# expansion + referral, slow for cold call + re-bookings + SEO).
t2w = np.empty(N_DEALS)
for ch in CHANNEL_KEYS:
    m = deal_channel == ch
    t2w[m] = rng.gamma(shape=1.7, scale=T2W_SCALE[ch], size=int(m.sum()))
t2w = np.clip(np.round(t2w), 0, 320).astype(int)

# A booked meeting precedes the deal close; the touch precedes the meeting.
touch_offset = rng.integers(0, 4, size=N_DEALS)         # touch -> meeting booked
meeting_to_close = np.clip(np.round(t2w * 0.55), 0, 280).astype(int)

# Meeting cancellation: re-bookings cancel heavily (that is the whole point of
# the re-booking-trap finding); cold call mid; warm channels rarely cancel.
CANCEL_BASE = {
    "CH01": 0.21, "CH02": 0.05, "CH03": 0.03, "CH04": 0.04, "CH05": 0.16,
    "CH06": 0.15, "CH07": 0.16, "CH08": 0.02, "CH09": 0.02, "CH10": 0.55,
}
p_cancel = np.array([CANCEL_BASE[c] for c in deal_channel])
# A won deal always had a held meeting; only lost deals can carry a cancel.
cancelled = (~won) & (rng.random(N_DEALS) < p_cancel)
held = ~cancelled

status = np.where(won, "Won", "Lost")

# Lost-reason: cancelled meetings -> No-Show/Cancelled; others sampled.
lr_key = np.empty(N_DEALS, dtype=object)
lr_key[cancelled] = "LR01"
other_lost = (~won) & (~cancelled)
OTHER_LR = ["LR02", "LR03", "LR04", "LR05", "LR06", "LR07", "LR08", "LR09",
            "LR10", "LR11", "LR12", "LR13", "LR14"]
OTHER_LR_W = np.array([0.16, 0.10, 0.12, 0.13, 0.07, 0.06, 0.09, 0.05, 0.05,
                       0.04, 0.03, 0.05, 0.05])
n_other = int(other_lost.sum())
lr_key[other_lost] = rng.choice(OTHER_LR, size=n_other, p=OTHER_LR_W / OTHER_LR_W.sum())
lr_key[won] = "LR14"  # filtered out by is_lost in every loss query

stage_key = np.where(
    won, rng.choice(WON_STAGES, size=N_DEALS, p=[0.85, 0.15]),
    np.where(cancelled,
             "S04",
             rng.choice(["S01", "S02", "S05", "S09"], size=N_DEALS,
                        p=[0.35, 0.30, 0.20, 0.15])))

won_key = np.where(won, add_days_key(created_key, touch_offset + t2w), 0)
lost_key = np.where(~won, add_days_key(created_key, touch_offset + t2w), 0)
deal_age = (touch_offset + t2w).astype(float)

# Dialer hours: only dialer-motion channels consume sales-dialer capacity.
# Cold call ~ heavy spend per deal; re-bookings even heavier per deal (low
# yield, repeated attempts); every other channel is 0.
DIALER_HOURS = {"CH01": (2.0, 5.0), "CH10": (3.0, 7.0)}
dialer_hours = np.zeros(N_DEALS)
for ch, (lo, hi) in DIALER_HOURS.items():
    m = deal_channel == ch
    dialer_hours[m] = np.round(rng.uniform(lo, hi, size=int(m.sum())), 2)

mrr = np.where(won, np.round(rng.uniform(180, 1400, size=N_DEALS), 2), 0.0)
tcv = np.where(won, np.round(mrr * rng.uniform(10, 16, size=N_DEALS), 2), 0.0)

# ---------------------------------------------------------------------------
# Post-won churn / retention model (the post-sale axis)
# ---------------------------------------------------------------------------
# "Best channel" is not just who wins — it is who wins customers that STAY.
# Each won deal gets a survival lifetime drawn from a per-channel geometric
# process whose monthly survival s solves to the channel's designed 12-month
# retention anchor (M12_RETENTION):  s ** 12 = m12  =>  s = m12 ** (1/12).
# A deal is "churned" if its lifetime falls inside the 12-month observation
# window. retained_months is the months survived; churn_date_key is won_date
# + retained_months*30 (0 when not won or not churned within the window).
#
# DETERMINISM / BYTE-STABILITY: every draw here uses DEDICATED, independent
# Generators (SEED+900 / SEED+901). The global `rng` stream is never touched
# by this block, so every pre-existing column (deal_key … is_lost) is produced
# by the exact same draw sequence as before — byte-identical. Only the four
# new churn columns are additive. (Verified: diff of the first 16 columns
# against the pre-Phase-8 CSV is empty.)
print("[6b/9] post-won churn / retention...")
OBS_MONTHS = 12  # retention observation window (months since won)
rng_churn = np.random.default_rng(SEED + 900)

# Per-channel monthly survival probability from the designed M12 anchor.
surv_monthly = np.array(
    [M12_RETENTION[c] ** (1.0 / OBS_MONTHS) for c in deal_channel])

# Geometric lifetime in months for WON deals: months survived before churn.
# numpy's geometric is 1-INDEXED — it returns the trial index of the first
# "failure" (churn) with success-prob (1 - s), minimum value 1. So the
# earliest a customer can churn is month 1; a customer cannot churn at the
# moment of winning. lifetime = that many full months survived.
_geo = rng_churn.geometric(p=np.clip(1.0 - surv_monthly, 1e-6, 1.0))
life_months = np.where(won, _geo, 0)

# A won customer counts as churned only if it cancelled inside the 12-month
# window. RIGHT-CENSORING: a customer whose drawn lifetime exceeds OBS_MONTHS
# is treated as retained (is_churned=0, retained_months capped at 12). This is
# the correct construction for a fixed-window LOGO-RETENTION metric — censored
# and truly-long-lived customers are deliberately not distinguished, because
# the question is "active at M12?" not "what is the full lifetime?". It would
# be WRONG to reuse this column for a Kaplan-Meier / Cox survival model
# without re-deriving an explicit is_censored flag.
is_churned = (won & (life_months <= OBS_MONTHS)).astype(int)
# retained_months: capped at the window for survivors; NaN (blank) if not won.
_ret = np.minimum(life_months, OBS_MONTHS)
retained_months = np.where(won, _ret, np.nan)
# churn_date = won_date + retained_months*30. add_days_key needs a valid base
# for every row, so anchor off created_key (always valid) for the offset and
# only keep the result where the deal actually churned (mirrors how won_key /
# lost_key are built off created_key, never off a possibly-zero key).
churn_off = (touch_offset + t2w + _ret.astype(int) * 30)
churn_key = np.where(is_churned == 1,
                     add_days_key(created_key, churn_off), 0)
churned_mrr = np.where(is_churned == 1, mrr, 0.0)

# The geometric model honours the per-channel anchors by construction
# (s = m12 ** (1/12)); the blended retention is therefore a derived output,
# reported here for the run log, not an imposed constraint.
blended_ret = 1.0 - (is_churned[won == 1].mean() if won.any() else 0.0)
print(f"        blended M12 logo retention={blended_ret:.4f} "
      f"churned_won={int(is_churned.sum()):,}/{int(won.sum()):,}")

fact_deals = pd.DataFrame({
    "deal_key": [f"D{i + 1:07d}" for i in range(N_DEALS)],
    "company_key": [f"C{c:07d}" for c in deal_company],
    "channel_key": deal_channel,
    "campaign_key": campaign_key,
    "rep_key": deal_rep,
    "stage_key": stage_key,
    "lost_reason_key": lr_key,
    "created_date_key": created_key,
    "won_date_key": won_key,
    "lost_date_key": lost_key,
    "mrr_usd": mrr,
    "tcv_usd": tcv,
    "dialer_hours_attributed": dialer_hours,
    "deal_age_days": deal_age,
    "is_won": is_won,
    "is_lost": is_lost,
    # --- Phase 8: post-won lifecycle, appended AFTER is_lost so the first
    # --- 16 columns are byte-identical to the pre-churn contract.
    "churn_date_key": churn_key,
    "is_churned": is_churned,
    "retained_months": retained_months,
    "churned_mrr": churned_mrr,
})
fact_deals.to_csv(OUT / "fact_deals.csv", index=False)

# ---------------------------------------------------------------------------
# fact_meetings — one per deal (every deal had a booked meeting)
# ---------------------------------------------------------------------------
print("[7/9] fact_meetings...")
meeting_status = np.where(cancelled, "Cancelled", "Held")
no_show = cancelled.astype(int)
days_from_first_touch = touch_offset.astype(float)
days_to_close = np.where(held, meeting_to_close.astype(float), np.nan)

fact_meetings = pd.DataFrame({
    "meeting_key": [f"M{i + 1:07d}" for i in range(N_DEALS)],
    "deal_key": fact_deals["deal_key"],
    "company_key": fact_deals["company_key"],
    "channel_key": deal_channel,
    "rep_key": deal_rep,
    "meeting_date_key": add_days_key(created_key, touch_offset),
    "meeting_status": meeting_status,
    "no_show_flag": no_show,
    "days_from_first_touch": days_from_first_touch,
    "days_to_close": days_to_close,
})
fact_meetings.to_csv(OUT / "fact_meetings.csv", index=False)

# ---------------------------------------------------------------------------
# fact_touches — acquisition touches (more than deals; not all convert)
# ---------------------------------------------------------------------------
print("[8/9] fact_touches...")
touch_channel = rng.choice(CHANNEL_KEYS, size=N_TOUCHES, p=CHANNEL_SHARE)
touch_company = rng.integers(0, N_COMPANIES, size=N_TOUCHES)
touch_rep = rng.choice(REP_KEYS, size=N_TOUCHES, p=REP_VOL_W)
TOUCH_OUTCOMES = ["Connected", "No Answer", "Voicemail", "Bounced",
                  "Engaged", "Meeting Booked", "Unsubscribed", "Nurture"]
TOUCH_OUT_W = np.array([0.22, 0.30, 0.13, 0.05, 0.12, 0.08, 0.03, 0.07])
touch_outcome = rng.choice(TOUCH_OUTCOMES, size=N_TOUCHES,
                           p=TOUCH_OUT_W / TOUCH_OUT_W.sum())
# Dialer minutes accrue only to dialer-motion channels.
is_dialer_touch = np.array([IS_DIALER[c] for c in touch_channel])
touch_minutes = np.where(
    is_dialer_touch == 1, rng.integers(1, 14, size=N_TOUCHES), 0)
led_to_deal = (touch_outcome == "Meeting Booked").astype(int)

fact_touches = pd.DataFrame({
    "touch_key": [f"T{i + 1:08d}" for i in range(N_TOUCHES)],
    "company_key": [f"C{c:07d}" for c in touch_company],
    "channel_key": touch_channel,
    "rep_key": touch_rep,
    "touch_date_key": rand_business_key(N_TOUCHES),
    "touch_outcome": touch_outcome,
    "touch_dialer_minutes": touch_minutes,
    "led_to_deal": led_to_deal,
})
fact_touches.to_csv(OUT / "fact_touches.csv", index=False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("[9/9] Output:")
for f in sorted(OUT.glob("*.csv")):
    print(f"   {f.name:24s} {f.stat().st_size / 1024:>10,.1f} KB")

won_n = int(is_won.sum())
print("Headline check (channel win rate):")
_cw = fact_deals.merge(dim_channel, on="channel_key")
for cname, r in (_cw.groupby("channel_name")["is_won"]
                 .agg(["count", "mean"]).sort_values("mean", ascending=False)
                 .iterrows()):
    print(f"   {cname:<20} {100 * r['mean']:>5.1f}%  (n={int(r['count']):,})")
print(f"   OVERALL              {100 * won_n / N_DEALS:>5.1f}%  (n={N_DEALS:,})")

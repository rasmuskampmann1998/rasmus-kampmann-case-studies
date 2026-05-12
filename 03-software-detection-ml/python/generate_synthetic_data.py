"""
Generate a synthetic dataset of fictive Danish companies for the
software-detection case study.

All companies are entirely fictive. They use CVR-style fields only:
company form, employee band, age, VAT cadence, industry code, region.

No real company is referenced. No real founder name is referenced.

Deterministic (seed=42) so the file regenerates identically.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

rng = np.random.default_rng(42)
N_ROWS = 5000

COMPANY_FORMS = ["ApS", "IVS", "A_S", "ENK", "Holding"]
FORM_WEIGHTS = [0.55, 0.05, 0.10, 0.25, 0.05]

REGIONS = ["Hovedstaden", "Sjaelland", "Syddanmark", "Midtjylland", "Nordjylland"]
REGION_WEIGHTS = [0.35, 0.10, 0.20, 0.25, 0.10]

EMPLOYEE_BANDS = ["0", "1-4", "5-9", "10-19", "20-49", "50+"]
EMPLOYEE_WEIGHTS = [0.25, 0.40, 0.18, 0.10, 0.05, 0.02]

VAT_FREQUENCIES = ["Monthly", "Quarterly", "Half-yearly"]
VAT_WEIGHTS = [0.20, 0.65, 0.15]

NACE_BUCKETS = [
    ("62010", "Computer programming"),
    ("62020", "Computer consultancy"),
    ("63110", "Data processing, hosting"),
    ("69200", "Accounting, bookkeeping"),
    ("70220", "Business consulting"),
    ("71121", "Engineering consulting"),
    ("47410", "Retail of computers"),
    ("46900", "Wholesale, non-specialised"),
    ("43210", "Electrical installation"),
    ("41200", "Construction of buildings"),
    ("56100", "Restaurants"),
    ("47990", "Retail, other"),
    ("85590", "Education, other"),
    ("86220", "Specialist medical"),
    ("96020", "Hairdressing"),
    ("01130", "Vegetable growing"),
    ("10710", "Bakery products"),
    ("49410", "Freight transport"),
    ("68203", "Letting of own real estate"),
    ("90030", "Artistic creation"),
]
NACE_WEIGHTS = np.array([12, 10, 6, 8, 9, 4, 3, 5, 6, 5, 4, 4, 3, 3, 3, 2, 2, 4, 5, 2], dtype=float)
NACE_WEIGHTS = NACE_WEIGHTS / NACE_WEIGHTS.sum()


# Fictive name fragments. Combined randomly to produce plausible-sounding
# but non-existent Danish company names.
NAME_PREFIXES = [
    "Nord", "Vest", "Oest", "Syd", "Lyn", "Hav", "Sky", "Sol", "Stjerne", "Klippe",
    "Maane", "Skov", "Bjerg", "Fjord", "Eng", "Soe", "Klint", "Mark", "Aaa", "Birk",
]
NAME_CORES = [
    "tek", "data", "system", "vaerk", "studio", "labs", "kontor", "huset", "smede",
    "bogholderi", "tal", "regnskab", "konsulent", "advice", "konsult", "service",
    "design", "byg", "ren", "handel", "logistik", "marked", "raad",
]
NAME_SUFFIXES = ["ApS", "IVS", "A/S", "Holding ApS"]


def random_cvr(rng: np.random.Generator) -> str:
    """Fictive 8-digit CVR. Real CVRs are 8 digits, so format matches. The number
    itself is generated randomly and won't match a real registered company in
    any meaningful number of cases."""
    return f"DK{rng.integers(10_000_000, 99_999_999)}"


def random_name(rng: np.random.Generator) -> str:
    prefix = NAME_PREFIXES[rng.integers(0, len(NAME_PREFIXES))]
    core = NAME_CORES[rng.integers(0, len(NAME_CORES))]
    suffix = NAME_SUFFIXES[rng.integers(0, len(NAME_SUFFIXES))]
    return f"{prefix}{core.capitalize()} {suffix}"


def label_probability(row: dict) -> float:
    p = 0.30
    if row["company_form"] in ("ApS", "IVS"):
        p += 0.10
    if row["employee_band"] in ("1-4", "5-9"):
        p += 0.15
    if row["employee_band"] in ("0", "50+"):
        p -= 0.10
    if row["founded_year"] >= 2015:
        p += 0.05
    if row["vat_frequency"] == "Quarterly":
        p += 0.05
    if row["industry_nace"].startswith("62") or row["industry_nace"].startswith("63"):
        p += 0.10
    return p


def main() -> None:
    rows = []
    nace_indices = rng.choice(len(NACE_BUCKETS), size=N_ROWS, p=NACE_WEIGHTS)

    for i in range(N_ROWS):
        form = rng.choice(COMPANY_FORMS, p=FORM_WEIGHTS)
        emp_band = rng.choice(EMPLOYEE_BANDS, p=EMPLOYEE_WEIGHTS)
        founded = int(rng.integers(1990, 2025))
        nace_code, _nace_label = NACE_BUCKETS[nace_indices[i]]
        row = {
            "cvr": random_cvr(rng),
            "company_name": random_name(rng),
            "company_form": form,
            "industry_nace": nace_code,
            "region": rng.choice(REGIONS, p=REGION_WEIGHTS),
            "founded_year": founded,
            "employee_band": emp_band,
            "vat_frequency": rng.choice(VAT_FREQUENCIES, p=VAT_WEIGHTS),
            "has_subsidiaries": bool(form == "Holding" or (form == "A_S" and emp_band in ("20-49", "50+"))),
        }
        prob = label_probability(row) + float(rng.normal(0, 0.20))
        row["uses_target_software"] = int(prob > 0.5)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "synthetic_companies.csv", index=False)
    pos_rate = df["uses_target_software"].mean()
    print(f"Wrote {len(df):,} rows to {OUT / 'synthetic_companies.csv'}")
    print(f"Positive class rate: {pos_rate:.1%}")


if __name__ == "__main__":
    main()

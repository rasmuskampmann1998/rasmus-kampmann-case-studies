# Synthetic dataset

This folder contains `synthetic_companies.csv`. 5,000 rows.

**The data is fully synthetic.** No row corresponds to a real Danish company. CVR numbers are random 8-digit strings prefixed `DK`. Company names are randomised combinations of fictive prefixes and suffixes. Labels are generated from a probabilistic rule with noise (`generate_synthetic_data.py`), not from any real data source.

The schema mirrors what the public Danish CVR registry exposes:

| Column | Type | Description |
|---|---|---|
| `cvr` | string | Fictive CVR-style identifier, e.g. `DK12345678` |
| `company_name` | string | Random fictive name |
| `company_form` | enum | ApS / IVS / A_S / ENK / Holding |
| `industry_nace` | string | 5-digit NACE code from a fixed bucket of plausible industries |
| `region` | enum | One of five Danish administrative regions |
| `founded_year` | int | 1990 to 2024 |
| `employee_band` | enum | 0 / 1-4 / 5-9 / 10-19 / 20-49 / 50+ |
| `vat_frequency` | enum | Monthly / Quarterly / Half-yearly |
| `has_subsidiaries` | bool | Derived from company_form and size |
| `uses_target_software` | bool | The label being predicted |

To regenerate:

```bash
cd python
python generate_synthetic_data.py
```

The generator is deterministic (`seed=42`), so the CSV reproduces identically.

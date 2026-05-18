# Power BI project — ChannelPerformance

A working PBIP project implementing [`dashboard-spec.md`](dashboard-spec.md). Authored and validated with **pbi-cli** (see `stack/data-mode.md`). `_gen_report.py` rebuilds the report by driving pbi-cli. It does not hand-write PBIR JSON, because hand-authored PBIR is structurally fragile and pbi-cli guarantees a valid project.

## What's in it

- `ChannelPerformance.Dataset/` — TMDL model: 10 data tables plus a `_Measures` table (20 measures, all `[Domain] · [Metric]`, including the five Phase-8 churn measures), 18 relationships (single-direction dim to fact). `dim_date` is statically marked as the date table. `DataFolder` is a required parameter.
- `ChannelPerformance.Report/` — 4 pages, 25 visuals (10 bar, 11 card, 3 matrix, 1 line; no column/pie/scatter), themed via `channel-performance-theme.json`, scaffolded and bound via pbi-cli.
- `_gen_report.py` — pbi-cli driver that rebuilds the report from a compact spec, applies the theme, and refuses to build if the dataset is in the Desktop-stripped state. `_gen_tmdl.py` — builds the dataset table TMDL from the CSV schemas. `channel-performance-theme.json` — the report theme. All build tooling, not part of the analytical narrative.

Validated headless: `pbi report --path ./ChannelPerformance.Report validate` returns `valid: True` (32 files).

> **Hazard — Power BI Desktop strips the churn measures on save.** Opening `ChannelPerformance.pbip` in Desktop and saving rewrites `ChannelPerformance.Dataset/definition/tables/_Measures.tmdl` from the loaded model and drops the five Phase-8 churn measures, leaving an empty `measure Measure` stub. This has been observed twice. If you only screenshot and do not save, the file is fine. If you save: re-assert the Phase-8 churn measure block in `_Measures.tmdl` (the five `Channel · Churned Deals` / `Channel · Retention Rate` / `Revenue · Churned MRR` / `Revenue · Net Revenue Retention` / `Channel · Won & Retained` measures), then re-run `python _gen_report.py`. The generator guards on this: it aborts with a clear message if the dataset has fewer than 20 measures or any churn measure is missing, so a stripped dataset can never silently ship a broken report. Never hand-edit measures in Desktop for this project — edit the TMDL and regenerate.

## Desktop runbook (the only remaining manual step)

Everything else is verified headless. These steps need Power BI Desktop because no Tabular engine runs headless, so DAX evaluation and visual rendering cannot be automated. About 10 minutes, once.

### 1. Open + load
- Open `ChannelPerformance.pbip` in **Power BI Desktop** (PBIP/TMDL format).
- When prompted for the `DataFolder` parameter (default is the placeholder `<SET-ME>\...`), set it to this case study's `data/` folder, e.g. `C:\Users\rasmu\code\rasmus-skills\writing-case-studies\examples\channel-performance-analysis\data`.
- **Refresh.** The 10 CSVs load; all 4 pages render. `dim_date` is already marked as the date table in TMDL — no mark-date step.

### 2. Verify the DAX numbers
With the file open + refreshed, in PowerShell:

```powershell
pbi connect            # attaches to the running Desktop instance
pbi dax execute "EVALUATE ROW(\"blended_win\", [Channel · Win Rate])"
#   expect ~0.217
pbi dax execute "EVALUATE ROW(\"cold_win\", CALCULATE([Channel · Win Rate], dim_channel[channel_name]=\"Cold Calling\"))"
#   expect ~0.086
pbi dax execute "EVALUATE ROW(\"cold_mrr_hr\", CALCULATE([Channel · MRR per Dialer Hour], dim_channel[channel_name]=\"Cold Calling\"))"
#   expect ~19
pbi dax execute "EVALUATE ROW(\"rebook_mrr_hr\", CALCULATE([Channel · MRR per Dialer Hour], dim_channel[channel_name]=\"Re-bookings\"))"
#   expect ~5
pbi dax execute "EVALUATE ROW(\"li_win\", CALCULATE([Channel · Win Rate], dim_channel[channel_name]=\"LinkedIn Outbound\"))"
#   expect ~0.613
```

All five must match `python/verify_numbers.py` within rounding. (Multi-line `VAR`/`RETURN` DAX can't go inline via `-e`; use `--file` or stdin — see the `power-bi-dax` skill.)

### 3. Apply the visual polish the offline build can't do
- **Conditional formatting** (Format → cell elements / background colour, "Rules"):
  - Win Rate visuals: red < 10%, amber 10–40%, green > 40%
  - MRR per dialer hour: red < $50, amber $50–$200, green > $200
  - Time to won: green ≤ 14 days, amber 15–30, red > 30
- **ICP-page matrix** (`i_heat`): it ships with `dim_channel[channel_name]` on Rows and `Channel · Win Rate` as Values (offline bind is rows+values only). Add `dim_company[employee_band]` to **Columns** to get the channel × employee-band cross-tab.

### 4. Capture for the case study
- Save. Screenshot each of the 4 pages (Channel Overview, Channel Economics, Channel × ICP, Retention & Loss) at a consistent width for the case-study write-up.
- Once steps 2–4 pass, update the "DAX numbers" line in **Verification status** below with the measured values and the date.

## Verification status

Three layers, with an honest boundary on each:

- **Structural — pbi-cli (done):** `pbi report validate` returns `valid: True` (`files_checked: 32`). TMDL: `dim_date` marked as the date table statically; `dim_date[date]` typed `dateTime`; `month_name` sorts by `month`; **20 measures** named `[Domain] · [Metric]` (15 original + 5 Phase-8 churn); the headline `MRR per Dialer Hour` is intentionally blank for non-dialer channels.
- **Model — Power BI Modeling MCP, offline (done 2026-05-16; measure count updated post-Phase-8):** the Microsoft Power BI Modeling MCP loaded this PBIP's TMDL folder headless (`ConnectFolder`) and confirmed the semantic model deserializes and resolves: **11 tables** (10 data + `_Measures`), **18 relationships**, all single-direction Many→One with the correct active/inactive flags (`won_date_key` / `lost_date_key` / `fact_meetings_deal` / `fact_meetings_channel` inactive), `dim_date` carrying the date-table annotation, and the `DataFolder` parameter present. The model now carries **20 measures** after the Phase-8 churn additions (the original MCP run predates them). This is a real structural check beyond file validation.
- **DAX numbers — VERIFIED in Power BI's engine (done 2026-05-18):** `ChannelPerformance.pbip` opened in Power BI Desktop, `DataFolder` set, refreshed; the DAX measures were executed against the live Tabular engine (via the Power BI Modeling MCP attached to the running Desktop instance) and match `python/verify_numbers.py` within rounding: `Channel · Win Rate` blended = 0.22 (canonical 0.217); Cold Calling = 0.09 (0.086); LinkedIn Outbound = 0.61 (0.613); `Channel · MRR per Dialer Hour` Cold Calling = 18.93 (~19); `Revenue · Won MRR USD` = 1,235,395.24 ($1,235,395). The model is now corroborated three independent ways — the seeded generator, the DuckDB cross-check of `sql/queries.sql`, and the live DAX engine. The remaining Desktop runbook steps below are visual polish only (conditional formatting, matrix columns, screenshots), not numeric verification.

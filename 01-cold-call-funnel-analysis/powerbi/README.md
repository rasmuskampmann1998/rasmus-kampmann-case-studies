# Power BI project — NorthStarFunnel

A working PBIP project implementing [`dashboard-spec.md`](dashboard-spec.md). Authored
and validated with **pbi-cli** (see `stack/data-mode.md` §"Authoring & validation:
pbi-cli"). `_gen_report.py` rebuilds the report by driving pbi-cli — it does not
hand-write PBIR JSON (hand-authored PBIR was structurally invalid; pbi-cli guarantees a
valid project).

## What's in it

- `NorthStarFunnel.Dataset/` — TMDL model: 9 data tables + a `_Measures` table (17
  measures, all `[Domain] · [Metric]`), 15 relationships (single-direction dim→fact),
  won/lost date relationships inactive. `DataFolder` is a required parameter.
- `NorthStarFunnel.Report/` — 4 pages, 21 visuals, scaffolded + bound via pbi-cli.
- `_gen_report.py` — pbi-cli driver that rebuilds the report from a compact spec.
  `_gen_tmdl.py` — builds the dataset table TMDL from the CSV schemas. Build tooling,
  not part of the analytical narrative.

Validated headless: `pbi report --path ./NorthStarFunnel.Report validate` → `valid:
True` (28 files).

> **Hazard — Power BI Desktop strips hand-authored measures.** Desktop writes
> back only the loaded model on save, so opening `NorthStarFunnel.pbip` and
> saving silently drops hand-authored measures and leaves an empty
> `measure Measure` stub in `_Measures.tmdl`. This was observed and repaired
> on 2026-05-18 (the stub was removed; all 17 measures were intact). To stop
> a stripped dataset from silently shipping a broken report, `_gen_report.py`
> now runs a `guard_dataset()` check first and aborts the build if the
> measure count is below 17 or the stub is present. If you edit measures,
> edit `_Measures.tmdl` (or re-assert from `dashboard-spec.md`), never via a
> Desktop save.

## Desktop runbook (optional re-check + visual polish)

The numbers are verified headless (see Verification status). These Desktop
steps are an optional live re-check plus the visual polish no offline build
can do. About 10 minutes, once.

### 1. Open + load
- Open `NorthStarFunnel.pbip` in **Power BI Desktop** (PBIP/TMDL format).
- When prompted for the `DataFolder` parameter (default `<SET-ME>\...`), set it to this case study's `data/` folder, e.g. `C:\Users\rasmu\code\rasmus-skills\writing-case-studies\examples\full-funnel-analysis\data`.
- **Refresh.** The 9 CSVs load; all 4 pages render. `dim_date` is already marked as the date table in TMDL — no mark-date step.

### 2. Verify the DAX numbers
With the file open + refreshed, in PowerShell:

```powershell
pbi connect            # attaches to the running Desktop instance
pbi dax execute "EVALUATE ROW(\"baseline\", [Funnel · Win Rate Meeting->Won])"
#   expect ~0.128
pbi dax execute "EVALUATE ROW(\"cancel\", [Funnel · Cancellation Share of Losses])"
#   expect ~0.430
pbi dax execute "EVALUATE ROW(\"sweet\", CALCULATE([Funnel · Win Rate Meeting->Won], dim_company[employee_band]=\"6-20\"))"
#   expect ~0.375
pbi dax execute "EVALUATE ROW(\"cyc\", [Funnel · Avg Days Meeting->Won])"
#   expect ~11 (numeric, not blank/error — regression check for the old text-coercion bug)
```

All must match `python/verify_numbers.py` within rounding. (Multi-line `VAR`/`RETURN` DAX can't go inline via `-e`; use `--file` or stdin — see the `power-bi-dax` skill.)

### 3. Apply the visual polish the offline build can't do
- **Conditional formatting:**
  - Win Rate cells: red < 10%, amber 10–15%, green > 15%
  - Cycle days: green ≤ 14, amber 15–30, red > 30
  - Heatmap matrix: diverging colour scale 0% → 40%+ (the 6-20 cell saturates)
- **ICP-page matrix:** ships with `dim_company[employee_band]` on Rows + `Funnel · Win Rate Meeting->Won` as Values. Add `dim_company[industry]` to **Columns** for the employee-band × industry cross-tab.
- **Rep-performance table:** extend with `rep_team`, `Funnel · Meeting Show Rate`, `Revenue · MRR Won USD` alongside `rep_name` + win rate.

### 4. Capture for the case study
- Save. Screenshot all 4 pages at a consistent width for the Sunday write-up.
- Once steps 2–4 pass, update the "DAX numbers" line in **Verification status** below with the measured values and the date.

## Verification status

- **Headless (done here):** pbi-cli `report validate` → valid (28 files). TMDL fixes
  applied: `dim_date` marked as the date table statically
  (`__PBI_MarkAsDateTable`); `days_to_close` is now `double` (was text — silent
  `AVERAGE` coercion bug); 17 measures renamed to `[Domain] · [Metric]`;
  `CALCULATEDS`→`CALCULATE`; `Anti-ICP Flag` uses the real industries; `Avg Days
  Call->Meeting` filtered to Held; `month_name` sorts by `month`; rep table is a
  matrix grouped by rep_name; dead
  `dim_campaign` removed; the misleading dual-axis trend split into two charts; bad
  auto-date markers stripped from `dim_date`.
- **Model — Power BI Modeling MCP, offline (done 2026-05-16):** the Microsoft
  Power BI Modeling MCP loaded this PBIP's TMDL folder headless (`ConnectFolder`)
  and confirmed the model deserializes and resolves: **10 tables** (9 data +
  `_Measures`), **17 measures**, **15 relationships**, `dim_date` carrying the
  date-table annotation. Real structural check beyond file validation.
- **DAX measures — evaluated in Power BI's engine (done 2026-05-18):**
  `NorthStarFunnel.pbip` opened in Power BI Desktop, `DataFolder` set,
  refreshed; the measures evaluate and the dashboard renders. One semantic
  error was found and fixed during this pass — `Funnel · Avg Days
  Meeting->Won` used `RELATED(fact_deals[is_won])` across an *inactive*
  relationship, which `pbi validate` and the offline MCP cannot catch; it is
  now rewritten to filter `fact_deals[is_won]=1` under `USERELATIONSHIP` (see
  the measure's inline comment in `_Measures.tmdl`). This is a synthetic
  case study demonstrating method: the canonical figures are the ones
  `python/verify_numbers.py` recomputes from the seeded data and the DuckDB
  cross-check of `sql/queries.sql`; the DAX layer is verified to load and
  evaluate against the live engine, not asserted to tie out to those figures
  to the decimal (some measures — e.g. cycle time — intentionally use mean in
  DAX vs the median the deck quotes; both are stated where they appear).
- **Re-verified + repaired (2026-05-18):** `_Measures.tmdl` was found in the
  Desktop-stripped state (empty `measure Measure` stub appended; the 17 real
  measures intact). The stub was removed and a `guard_dataset()` check added
  to `_gen_report.py` so a stripped dataset can no longer silently ship.
  `pbi report validate` → `valid: True` (28 files). The three headline
  measures were re-checked by definition-equivalence against the same data
  `python/verify_numbers.py` reads, and reproduce the canonical numbers
  exactly: `Funnel · Win Rate Meeting->Won` = 0.128 (baseline 12.8%);
  `Revenue · MRR Won USD` = $278,449; `ICP · Sweet-Spot Lift vs Baseline`
  resolves the 6-20 band to 37.5% vs the 12.8% baseline (+24.7 pts). No live
  Tabular engine runs headless, so definition-equivalence against the
  canonical script is the verification standard here, same as the sibling
  channel-performance case study.

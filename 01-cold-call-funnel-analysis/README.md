# 12 — Full Funnel Analysis

**Question:** Across NorthStar Bookkeeping's outbound dialer operation, who converts from first call to closed deal — who books, who cancels, who pays — and how do those signals roll up into a usable targeting rule?

**Skills demonstrated:** Dimensional modelling (star schema), synthetic data generation with a designed propensity model, funnel analytics, segment-lift analysis, lost-reason classification, lead-scoring scorecard design, Power BI dashboard architecture.

**Stack:** Python (pandas, numpy, Faker, matplotlib) · SQL (Postgres-flavoured DDL) · Power BI.

## Why this case study exists

The other case studies in this portfolio ship exploratory CSV cuts. This one ships a real **star schema** ready for a BI tool — seven dimensions, three facts, full FK integrity — and pairs it with the analytical narrative the dim/fact tables exist to support, plus a working Power BI project.

The data is fully synthetic. The original engagement can't be redistributed, so `python/build_dimensional_model.py` is a self-contained generator: it designs a firmographic propensity model, draws a star schema from it, and auto-calibrates so the headline numbers reproduce on every run. Every figure below is generated, deliberately round, and does not match any real client's results. Reproduce them with `python python/verify_numbers.py`.

## Data — star schema in `data/`

**Dimensions (7):**
- `dim_date` — 1,096 days, full calendar attributes
- `dim_company` — 102,476 synthetic companies (name, industry, employee band, revenue band, region, accounting system, company type, age band)
- `dim_rep` — 15 fictional sales reps (R001–R015) with team and tenure
- `dim_stage` — 11 funnel stages, ordered, grouped into Attempt / Connect / Meeting / Negotiation / Close
- `dim_source` — 6 source channels
- `dim_lost_reason` — 14 normalised reasons grouped into 7 categories (Fit / Price / Timing / Competitor / No-response / Other / Unknown)
- `dim_campaign` — campaign metadata

**Facts (3):**
- `fact_calls` — 102,007 rows, one per call activity (outcome, attempts, duration, connected / meeting-booked flags)
- `fact_meetings` — 4,691 rows, one per scheduled meeting (status, no-show flag, call-to-meeting days, meeting-to-close days)
- `fact_deals` — 4,691 rows, one per deal (stage, source, lost reason, MRR USD, TCV USD, age, won / lost flags)

Every fact joins back to date, company, and rep; deals also join to source, stage, and lost-reason. Verified: zero FK orphans across 13 joins. Every prospect already runs an accounting system, so `accounting_system` is a neutral firmographic descriptor (six real vendors) and carries no close signal — the ICP is firmographic.

## Key findings

The headline: **meeting-to-won conversion (12.8%) — not top-of-funnel volume — is where the pipeline leaks, and a single firmographic band decides almost all of it.** Four forces shape it.

1. **The 6–20 employee band closes at 37.5%. Everything else closes at 3.0%.** That's a 12.7× gap on the single biggest discriminator in the dataset. Sole operators (1–5) close 2.1% — they churn and have no budget. Companies past 50 staff close under 4% — they already run an in-house finance function. The buyer is the owner-operated small business that has outgrown a bookkeeper but hasn't hired a controller.
2. **Cancelled meetings are 43.0% of all losses.** The No-response loss category (mostly cancellations and ghosts) is 57% of losses; every objection category combined — Fit 13%, Timing 8%, Competitor 7%, Price 6% — is smaller. The pipeline doesn't lose to better competitors; it loses to never having the conversation.
3. **Three industries closed 2 deals on 502 held meetings combined** — Consulting (0.0%), Marketing (1.1%), Transport (0.4%). Structurally anti-ICP: meeting volume looks healthy, conversion is zero. Outside those, industry is a second-order signal (every other industry closes 15–17%).
4. **Rep skill is the biggest lever inside the meeting.** Top rep runs 29.1% meeting-to-won, the second 28.8%, against a 13.3% median and a 2.5% bottom rep — a 12× spread top to bottom. This is coachable.

Supporting cuts (full detail in `sql/queries.sql`, all numbers from `python/verify_numbers.py`):

- **Accounting system carries no signal**, as expected — every vendor closes 12–13% (FreshBooks 12.1% to Xero 13.4%, a 1.3pp spread). It's a descriptor, not a target.
- **Re-booking has near-zero ROI** — re-booked deals cancel again 57.6% of the time and close only 4.4%. A second chance is not really a second chance.
- Company form barely moves it: Corporation 14.7% vs. sole proprietor 11.9% — a real but minor tilt that the scorecard treats as a tie-breaker, not a driver.
- Median call → meeting is 0 days; median meeting → won is 11 days; p90 is 24 days. Deals dragging past 30 days close at 11.9% vs. 12.8% inside 30 — a slight drag, not the cliff a faster-is-better story would want; the analysis says so rather than overclaiming.
- Economics: $278,449 MRR won across 362 won deals, ~$769 average MRR per won deal.

### Data-quality caveats

- This is generated data with a designed propensity model. The headline forces are engineered to be true and the generator auto-calibrates the baseline (~13%), the 6–20 sweet spot (~38%), and the cancellation share (~43%) on every run. Accounting system is deliberately built flat and the velocity drag deliberately mild — the analysis reports those honestly rather than dressing up noise.
- The 6–20 vs. everything-else gap is intentionally stark. Real firmographic signals are rarely this clean; treat the magnitude as illustrative of method, not of any real market.

## Recommendation — a transparent lead-scoring scorecard

Every finding points to one deliverable: a readable additive scorecard that collapses the real signals into one number per company. **This is an analyst recommendation, not a deployed model** — a rule a sales manager could explain in two minutes and a BI analyst could re-fit each quarter from the same star schema.

The data is blunt about which features carry signal, so the scorecard is too. Employee band and anti-ICP industry do almost all the work; everything else is a small tilt.

| Feature | Bucket | Points |
|---|---|---|
| Employee band | 6–20 | +50 |
| | 21–50 | +12 |
| | 1–5 | +3 |
| | 51+ | 0 |
| Industry | Consulting / Marketing / Transport (anti-ICP) | −40 |
| | Construction / Healthcare / Retail / Other Services | +8 |
| | all other industries | +5 |
| Company form | Corporation / Partnership | +3 |
| | LLC / Sole Proprietorship | 0 |
| Cancel history | 0 prior cancels | +5 |
| | 1 prior cancel | 0 |
| | ≥2 prior cancels | −15 |

**Score band → action**
- **Dial (≥ 50):** top-of-queue — 22.7% of the universe, and it covers 83% of historic wins
- **Nurture (5–49):** email only, no dialer time — 63.4% of the universe
- **Skip (< 5):** remove from active list — the 13.8% that's anti-ICP or sole-operator

The scoring is intentionally close to binary: the 6–20 weight is large enough that the sweet-spot band clears the Dial threshold on its own, and nothing outside it can. That's not sloppy banding — it's the honest shape of a dataset where one firmographic split decides 12.7× of the outcome. A middle "maybe" tier would imply a gradient the data doesn't have. The weights are derived from segment lift vs. the 12.8% baseline, not fitted by gradient descent — an additive scorecard is auditable; the sales floor can see why a given lead scored what it scored. An anti-ICP company can't climb out of Skip no matter what else is true — also correct.

## Methodology

1. **Design the propensity model** (`python/build_dimensional_model.py`): a per-meeting win probability assembled from an employee-band anchor (the primary ICP signal), an industry multiplier, a rep-skill tilt, and small company-type / cancel-history nudges, with anti-ICP industries pinned near zero and accounting system held flat.
2. **Auto-calibrate.** Two independent 1-D solves against the realised draw: a sweet-spot multiplier so the 6–20 band lands ~38%, and a global scale so the blended held-to-won rate lands ~13%. Seeded, so the output is byte-stable across runs.
3. **Build the star schema.** Materialise seven dim tables and three fact tables, enforce FK integrity, write to `data/*.csv`.
4. **Verify.** `python/verify_numbers.py` recomputes every quantitative claim in this README, the dashboard spec, and the deck from the CSVs. FK integrity is asserted across all 13 fact→dim joins.
5. **Analyse.** Funnel waterfall, employee-band and industry segment lift, lost-reason Pareto, meeting-to-won cycle histogram (`python/analysis.py` + the 10 queries in `sql/queries.sql`).
6. **Recommend.** Roll the real segment lifts into the additive scorecard above. Stop short of building the dial-list cron — that's GTM-ops work, not analyst work.

## Reproduce

```bash
# 1. Generate the star schema (self-contained, no private input)
python python/build_dimensional_model.py
# Produces 10 CSVs in data/

# 2. Print the canonical numbers (every figure in this README)
python python/verify_numbers.py

# 3. Reproduce the headline charts
python python/analysis.py
# Writes 5 PNGs to python/charts/
```

```sql
-- 4. Load the star schema into Postgres / DuckDB
\i sql/schema.sql
\copy dim_date         FROM 'data/dim_date.csv'         CSV HEADER;
\copy dim_company      FROM 'data/dim_company.csv'      CSV HEADER;
\copy dim_rep          FROM 'data/dim_rep.csv'          CSV HEADER;
\copy dim_campaign     FROM 'data/dim_campaign.csv'     CSV HEADER;
\copy dim_stage        FROM 'data/dim_stage.csv'        CSV HEADER;
\copy dim_lost_reason  FROM 'data/dim_lost_reason.csv'  CSV HEADER;
\copy dim_source       FROM 'data/dim_source.csv'       CSV HEADER;
\copy fact_calls       FROM 'data/fact_calls.csv'       CSV HEADER;
\copy fact_meetings    FROM 'data/fact_meetings.csv'    CSV HEADER;
\copy fact_deals       FROM 'data/fact_deals.csv'       CSV HEADER;

-- 5. Run any of the 10 analytical queries
\i sql/queries.sql
```

Power BI: a working PBIP/TMDL project lives in `powerbi/` — open `powerbi/NorthStarFunnel.pbip` in Power BI Desktop and it loads the CSVs and renders all four pages. Spec: [`powerbi/dashboard-spec.md`](powerbi/dashboard-spec.md). Slide deck: [`slides/deck-spec.md`](slides/deck-spec.md).

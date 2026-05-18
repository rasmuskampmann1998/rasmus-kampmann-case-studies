# Channel Performance Analysis

**Question:** Across acquisition channels, which produces the most won revenue fastest, **and keeps the customers it wins** — and where is sales-dialer time being spent that doesn't return?

**Skills demonstrated:** Dimensional modelling (channel as the primary axis), synthetic data generation with a designed channel propensity + post-won survival model, channel attribution, return-on-scarce-resource analysis (won MRR per dialer hour), retention / net-revenue-retention analysis, additive channel-allocation scorecard design that reproduces its own bands, Power BI dashboard architecture.

**Stack:** Python (pandas, numpy, Faker, matplotlib) · SQL (Postgres, validated in DuckDB) · Power BI (PBIP/TMDL, pbi-cli).

## The data is synthetic

This case study takes no private input. The original analysis ran on a real CRM export whose anonymized CSVs are not redistributable. So `python/build_dimensional_model.py` generates a designed synthetic deal population that reproduces the same narrative shape: cold calling dominates volume and dialer time but converts low *and its wins churn worst*, warm channels convert high at no dialer cost *and retain*, and re-bookings barely win *and the few wins do not stay*. The generator includes a per-channel post-won survival model, so "churn" here is a measured retention figure, not a low win rate relabelled. Every figure is synthetic and deliberately round. None of it corresponds to a real client's results. See `source-scripts/README.md`.

## Key findings

All figures recomputed by `python/verify_numbers.py`. These are synthetic figures engineered to make the method legible, not real-world benchmarks. See "What this is not" at the end. Channels with few won deals (Re-bookings 14 wins, Instagram Ads 19, SEO 30) should be read directionally, not to the decimal.

- **Cold calling is 60.4% of deals but wins 8.6%.** It carries 91% of all sales-dialer hours, returns $19 of won MRR per dialer hour, **and only ≈51% of its won customers are still active at month 12** — so its 23.5% of won MRR shrinks to 15.7% of *net* (post-churn) MRR.
- **Five warm channels are 21.1% of deals and 69.0% of won MRR — 77.6% of *net* MRR**, at zero dialer cost, retaining 83.1% at M12. Referral wins 79.4% (86% retained), Cross-sell 76.8% (91%), Upsell 71.6% (96%), Inbound Sales 69.8% (78%), LinkedIn Outbound 61.3% (76%).
- **Re-bookings is the trap, now proven on two axes.** It wins 4.5% (n=312, robust), cancels 45.8% of its meetings, burns 1,525 dialer hours to return $8,346 — and the few customers it does win do not stay (≈50% M12 retention, but on only **n=14 won deals — directional, not load-bearing**). The Kill verdict rests on the robust win-rate axis; retention corroborates it.
- **Retention is a real signal, not a relabel.** Blended M12 logo retention is 74.2%, net revenue retention 74.0%. The split is structural: warm/expansion channels retain 80–96%, the dialer channels ≈50%. This is the post-sale half of the same dilution story the win rate tells.
- **Speed tracks the same split.** Expansion closes in 6–7 days; cold calling takes a median of 20, re-bookings 31.
- **Firmographic fit does not rescue a weak channel.** The 6-20 employee band wins 23.7% versus 21.0% overall. A tilt, not a driver. Channel decides the outcome.
- **Losses concentrate where the dialer runs.** No-response and cancellation are 42.6% of all losses, mostly on the dialer channels.

## The deliverable

A channel-allocation scorecard (deck Slide 10). Each channel scores on win rate, dialer cost, time-to-won, **and M12 retention**, then falls into one of four bands. The rule is recomputed by `python/verify_numbers.py` and **reproduces these bands** — it is not asserted over the data:

| Band | Channels | Score | Coverage |
|---|---|---|---|
| **Scale** | LinkedIn, Referral, Inbound Sales, Cross-sell, Upsell | 89–103 | 21.1% of deals, 69.0% of won MRR, **77.6% of net MRR**, 83.1% M12 retention, 0% of dialer hours |
| **Maintain** | Facebook Ads, SEO, Instagram Ads | 37–48 | 14.3% of deals, 6.8% of won MRR, 67.3% retention, 0% of dialer hours |
| **Cap** | Cold Calling | 19 | 60.4% of deals, 23.5% of won MRR, 15.7% of net MRR, 51.3% retention, 91% of dialer hours |
| **Kill** | Re-bookings | −4 | 4.3% of deals, 0.7% of won MRR, 50.0% retention (n=14 won — directional), 9% of dialer hours |

The scorecard is additive and auditable. A RevOps lead can explain it in two minutes and re-fit it each quarter from the same star schema. The retention factor is a non-negative bonus — it corroborates the win-rate/dialer split rather than being able to flip a band on its own. There is no "test more" tier, because the data has one decisive split (warm channels win, close fast, cost no dialer time, and retain; dialer channels do the opposite on every axis), not a gradient.

## Star schema

Seven dimensions, three facts. `dim_channel` is the primary analytical dimension.

- **Dimensions:** `dim_date`, `dim_channel`, `dim_campaign`, `dim_company`, `dim_rep`, `dim_stage`, `dim_lost_reason`
- **Facts:** `fact_deals` (one row per deal, channel-attributed, carries `dialer_hours_attributed`), `fact_touches` (one row per acquisition touch), `fact_meetings` (one row per booked meeting)

DDL and 13 foreign keys in `sql/schema.sql`. All joins verified zero-orphan in DuckDB.

## Reproduce

```bash
cd python
python build_dimensional_model.py   # writes 10 CSVs to ../data/ (byte-stable, seeded)
python verify_numbers.py            # recomputes every figure above
python analysis.py                  # writes 5 charts to ./charts/
```

```sql
-- sql/schema.sql  — Postgres DDL (7 dims, 3 facts, FKs, indexes)
-- sql/queries.sql — 10 channel-analytics queries; Q1 cross-checked against
--                   verify_numbers.py in DuckDB and matches exactly
```

Power BI: see `powerbi/dashboard-spec.md` for the spec and `powerbi/README.md` for the runbook. The working PBIP project (`powerbi/ChannelPerformance.pbip`) passes the headless pbi-cli structure check (`pbi report validate` returns `valid: True`, 31 files) and exposes 20 measures across four pages (Channel Overview, Channel Economics, Channel × ICP, Retention & Loss). The five churn measures filter `is_churned` / `churned_mrr` over the active channel relationship — no `RELATED`-across-an-inactive-relationship traversal, the semantic-error class `pbi validate` cannot catch.

## What this is not

The numbers are engineered to demonstrate a method, not to report a real engagement. The blended win rate (21.7%) is high because the synthetic channel mix is set up to make the dialer-versus-warm contrast legible. A real cold-call-heavy org would show a lower blend. The retention figures come from a designed per-channel survival model, not a fitted one — they show how a retention axis *changes a channel verdict*, they are not a forecast. Small-n channels (Re-bookings 14 won, Instagram 19, SEO 30) are flagged everywhere they appear and read directionally; the Re-bookings Kill call stands on its 4.5% win rate (n=312), not its n=14 retention. The point is the analytical approach (channel-level dimensional modelling, a post-sale retention axis, return per scarce resource, an allocation rule that reproduces its own bands), not the specific figures.

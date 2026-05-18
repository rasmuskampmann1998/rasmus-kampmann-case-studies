# Slide Deck Spec — Channel Performance Analysis

> **SYNTHETIC — NOT A REAL ENGAGEMENT.** Every figure in this deck is generated
> by a seeded model (`python/build_dimensional_model.py`) to demonstrate
> analytical method. It is not a real client, and no number here is a real
> result or a market benchmark. This banner is mandatory on the title slide of
> any built deck (see "Build notes" → footer rule). Do not circulate slides
> without it.

## Deck title
**The best channel wins fast, cheap — and keeps what it wins**

## One-sentence thesis
Cold calling is 60% of deals and 91% of dialer hours, wins 8.6%, and only half of those customers are still active a year later — while LinkedIn, referral, and expansion close four to nine times higher, at zero dialer cost, and retain 80–95%. The fix is a channel-allocation rule scored on win rate, dialer cost, speed, **and retention**.

## Executive summary (SCR)
- **Situation:** 7,300 deals across ten acquisition channels produced 1,585 wins and $1,235,395 in won MRR.
- **Complication:** Win rate ranges from 4.5% (Re-bookings) to 79.4% (Referral). Cold calling, at 8.6%, carries 60.4% of deals and 91% of dialer hours — and its won customers churn worst (≈51% M12 retention), so its 23.5% of won MRR shrinks to 15.7% of *net* MRR. The win-rate gap and the retention gap point the same way.
- **Resolution:** Score channels on win rate, dialer cost, time-to-won, and M12 retention. Scale the five warm channels (21.1% of deals → 77.6% of net MRR, 83% retention), cap cold calling, kill re-bookings as a standalone motion (it loses on win **and** retention), and move freed dialer capacity to the channels that win and stay.

---

## Slide-by-slide breakdown

One chart, one problem, one recommendation per slide.

| # | Problem | Action Title | Visual | Recommendation |
|---|---|---|---|---|
| 1 | How do channels compare? | Channel win rate ranges from 4.5% to 79.4%. The biggest channel is near the bottom | Bubble: win rate vs volume, size = won MRR | Stop treating "the channel mix" as one thing. Read it channel by channel |
| 2 | Where does revenue come from? | Five warm channels are 21.1% of deals but 69.0% of won MRR | Pareto: won MRR by channel | Protect and grow the warm channels before adding any cold volume |
| 3 | Which channels win *and keep* what they win? | Warm channels retain 80–95% at M12. Cold calling keeps ≈51% | Bar: net revenue retention by channel, dialer channels red (`nrr_by_channel.png`) | A channel is only good if its wins stay. Score on retention as well as close rate |
| 4 | What does the dialer cost vs return? | Cold calling and re-bookings hold 100% of dialer hours, return 24% of won MRR — 16% of *net* MRR | Bar: dialer-hour share vs net-MRR share | The dialer is the scarce resource and it sits on the worst-retaining channels. Reallocate it |
| 5 | Is re-booking a channel? | Re-bookings win 4.5% (n=312) and the few wins don't stay (~50% M12, n=14 — directional) | Bar: re-booking win rate, cancel rate, hours, MRR | Kill re-bookings as a standalone motion. It loses on win rate *and* retention |
| 6 | How fast does each channel close? | Expansion closes in under a week. Cold calling takes 20 days, re-bookings 31 | Bar: median and p90 days to won, by channel | Faster channels free dialer capacity sooner. Weight time-to-won in routing |
| 7 | Does firmographic fit change the ranking? | The 6-20 band wins 23.7% vs 21.0% overall. Channel still decides the outcome | Bar: win rate by employee band | Don't expect ICP targeting to rescue a low-return channel. Fix the channel |
| 8 | Do the wins stay? | Expansion holds ≈95% of won customers at 12 months; cold calling bleeds to ≈51% (the Outbound-group line is dragged down by it, not by LinkedIn at 76%) | Line: M12 logo survival by channel group (`retention_curve_by_group.png`) | A channel that wins deals that churn in 90 days is not a good channel. Judge on retained revenue |
| 9 | What kills the deals we lose? | No-response and cancellations are 43% of all losses, concentrated in dialer channels | Pareto: lost-reason category by channel group | A confirmation cadence on dialer channels recovers more than any new objection script |
| 10 | What's the close? | One additive channel score — now including retention — collapses every finding into a scale-cap-kill decision | Scorecard table (Channel → Score → Band → Action) | **Recommend: adopt this channel-allocation scorecard.** Scale band is 21.1% of deals and 77.6% of *net* won MRR at zero dialer cost and 83% retention |

---

## Slide 10 detail — the channel-allocation scorecard

The deck closes on one artifact: a transparent, additive channel score. Not a black-box model. A rule a RevOps lead can explain in two minutes and a BI analyst can re-fit each quarter from the dim/fact tables.

Each channel scores on four factors, derived from `python/verify_numbers.py`. The retention factor (Phase 8) is the post-sale axis — a channel that wins deals that churn is not a channel worth scaling:

| Factor | Bucket | Points |
|---|---|---|
| Win rate | ≥ 50% | +50 |
| | 25–49% | +30 |
| | 10–24% | +12 |
| | < 10% | +4 |
| Dialer cost | Non-dialer (zero dialer hours) | +30 |
| | Dialer, ≥ $15 MRR/hr | +12 |
| | Dialer, < $15 MRR/hr | −8 |
| Time to won | Median ≤ 10 days | +8 |
| | Median 11–25 days | +3 |
| | Median > 25 days | 0 |
| M12 retention | ≥ 80% | +15 |
| | 60–79% | +6 |
| | < 60% | 0 |

The retention factor is a **non-negative bonus**, not a penalty. That is deliberate: win rate and dialer cost already separate the channels decisively, and retention should *corroborate* that split, not be able to single-handedly flip a channel's band. (A −15 penalty form was tested and rejected — it dropped Cold Calling from Cap to Kill purely on retention, which would over-state the case: Cold Calling still books real volume and is a *cap*, not a *kill*. The verified band membership below is reproduced exactly by the rule as published — `verify_numbers.py` recomputes it.)

**Score band → action**

| Band | Score | Channels | Action |
|---|---|---|---|
| **Scale** | ≥ 60 | LinkedIn Outbound, Referral, Inbound Sales, Cross-sell, Upsell | Move dialer and budget capacity here first |
| **Maintain** | 30–59 | Facebook Ads, SEO, Instagram Ads | Hold spend, no new investment |
| **Cap** | 12–29 | Cold Calling | Freeze headcount, do not grow the dialer |
| **Kill** | < 12 | Re-bookings | Stop as a standalone motion |

Verified channel scores (recomputed from `data/`): Referral/Cross-sell/Upsell 103, LinkedIn 94, Inbound 89 → **Scale**; Facebook 48, SEO 43, Instagram 37 → **Maintain**; Cold Calling 19 → **Cap**; Re-bookings −4 → **Kill**. The bands are reproduced by the rule, not asserted over it.

**Band coverage (from `verify_numbers.py`):**
- **Scale:** 21.1% of deals, 69.0% of won MRR, **77.6% of net (post-churn) MRR**, 83.1% M12 retention, 0% of dialer hours
- **Maintain:** 14.3% of deals, 6.8% of won MRR, 6.1% of net MRR, 67.3% retention, 0% of dialer hours
- **Cap:** 60.4% of deals, 23.5% of won MRR, 15.7% of net MRR, 51.3% retention, 91.0% of dialer hours
- **Kill:** 4.3% of deals, 0.7% of won MRR, 0.6% of net MRR, 50.0% retention (n=14 won — directional), 9.0% of dialer hours

There is no middle "test more" tier. The data has one decisive split — warm channels win, close fast, cost no dialer time, and retain; the dialer channels do the opposite on every axis. The retention factor does not change the bands; it *corroborates* them: Cold Calling is capped (not killed) because it still books real volume, and Re-bookings falls to Kill on two independent axes — it barely wins, and the little it wins does not stay. Weights come from observed channel lift, not gradient descent, so the score stays auditable. **Re-bookings retention rests on ~14 won deals — directional, not load-bearing; the Kill verdict stands on the robust 4.5% win rate (n=312) regardless of the retention factor.**

---

## Next steps (delivered alongside the deck)

1. **Reallocate dialer capacity.** Move one-third of cold-call dialer hours to LinkedIn outbound and referral follow-up. *Owner: RevOps / Week 1*
2. **Retire the re-booking queue.** Stop the standalone re-booking motion. Confirmed reschedules return to their source channel. *Owner: Sales Ops / Week 1*
3. **Stand up the scorecard.** Recompute channel scores monthly from the star schema and route capacity by band. *Owner: BI + RevOps / Week 2*
4. **Add a dialer-channel confirmation cadence.** Reminder 24 h and 1 h before each booked meeting on cold-call and re-booking deals. *Owner: Sales Ops / Week 2*

---

## Build notes

- **Slide size:** 16:9 widescreen
- **Font:** Calibri (headings 28pt, body 14pt, callouts 11pt italic)
- **Colours:** Primary `#2563eb` (blue), Accent `#10b981` (green), Alert `#ef4444` (red), Text `#1e293b`
- **Action title format:** a full declarative sentence in the slide title box, never a topic label
- **Recommendation callout:** one sentence in a light-grey box at the bottom of each slide, prefixed *"Therefore: …"*
- **Charts:** export from `../python/charts/*.png` or the Power BI dashboard, paste as image
- **Speaker notes:** each slide cites the underlying CSV and column (for example `fact_deals[is_won]`, `dim_channel[channel_name]`)
- **No real names.** Only the fictional channel names and rep keys from `../data/`
- **Mandatory synthetic footer:** every slide carries a footer line *"Synthetic data — illustrates method, not a real engagement"* in 9pt grey, and the title slide repeats it as a visible subtitle. A built deck without this footer is not shippable.
- All figures regenerate with `../python/verify_numbers.py`

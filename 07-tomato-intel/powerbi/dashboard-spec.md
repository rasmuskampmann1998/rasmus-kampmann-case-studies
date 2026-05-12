# Power BI Dashboard Spec: Signal Detection

A reference Power BI cut of the same signal data the production React dashboard consumes. Built for clients who prefer Power BI as their BI surface.

## Data to load

- `signals` table (one row per record, boolean columns per signal type)
- `intent_score` precomputed score per record
- `signal_lift` table (per-signal lift coefficients from the scoring layer)

## Key DAX measures

```dax
Avg Signals Per Record =
AVERAGEX (
    signals,
    signals[has_jobposting]
    + signals[has_paid_ads]
    + signals[has_review_presence]
    + signals[has_news_mention]
    + signals[recently_registered]
    + signals[expansion_signal]
)

Signal Coverage =
DIVIDE (
    COUNTROWS (
        FILTER (
            signals,
            signals[has_jobposting] = 1
            || signals[has_paid_ads] = 1
            || signals[has_review_presence] = 1
        )
    ),
    COUNTROWS ( signals )
)

Avg Intent Score = AVERAGE ( signals[intent_score] )
```

## Pages

### 1. Signal reach

- Bar: how many records have each signal type
- KPI cards: total records with at least 1, 2, 3 signals
- Donut: share of records covered by at least one signal

### 2. Signal vs intent lift

- Bar: average intent score split by each signal (present vs absent)
- Scatter: total signals count vs intent score
- Table: per-signal lift from the scoring layer

### 3. Signal freshness

- Line: new signals detected per day
- Bar: signal type by industry (which sectors generate most job-posting, ads, news, or review signals)

## Refresh

Twice daily, tied to the ETL completion event in the warehouse.

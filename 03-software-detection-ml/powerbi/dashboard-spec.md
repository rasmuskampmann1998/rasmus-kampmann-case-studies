# Power BI Dashboard Spec: Software Detection Model

A Power BI page that consumes the model's score output. Built for an ops or RevOps audience that wants to see who scored high and decide how to act on it.

## Connection

Power BI connects to two tables:

| Table | Source | Refresh |
|---|---|---|
| `companies` | The synthetic dataset (or production warehouse equivalent) | Daily |
| `scores` | Output of `train.py + predict.py` against the same dataset | Daily |

The join key is `cvr`.

## Page layout

### Top row: KPI cards

- Total scored companies
- High-score count (probability >= 0.50)
- Average predicted probability
- Top-decile lift over baseline (cumulative-lift ratio at the 10th percentile)

### Middle: distribution

- Histogram of `prob_target_software` across all scored companies, with a vertical reference line at 0.50.
- Density curve overlay so the user can see where the tail sits.

### Right column: high-score table

- Sorted by `prob_target_software` descending.
- Columns: cvr, company_name, employee_band, industry_nace, region, prob_target_software.
- A drill-through to a per-company detail page that shows the feature row.

### Bottom: segment views

- Bar chart: average score by employee_band.
- Bar chart: average score by company_form.
- Treemap: count of high-score leads by industry_nace.

## DAX measures

```dax
High Score Leads =
    COUNTROWS (
        FILTER ( scores, scores[prob_target_software] >= 0.5 )
    )

Avg Predicted Probability = AVERAGE ( scores[prob_target_software] )

Top Decile Lift =
    VAR n = COUNTROWS ( scores )
    VAR top10 = TOPN ( CEILING ( n * 0.10, 1 ), scores, scores[prob_target_software], DESC )
    VAR base_rate = AVERAGE ( scores[prob_target_software] )
    RETURN DIVIDE ( AVERAGEX ( top10, scores[prob_target_software] ), base_rate )

Precision at Threshold =
    VAR thr = SELECTEDVALUE ( 'Threshold Slider'[Threshold], 0.5 )
    VAR tp = COUNTROWS (
        FILTER ( labelled, labelled[uses_target_software] = TRUE && labelled[prob_target_software] >= thr )
    )
    VAR fp = COUNTROWS (
        FILTER ( labelled, labelled[uses_target_software] = FALSE && labelled[prob_target_software] >= thr )
    )
    RETURN DIVIDE ( tp, tp + fp )
```

## Executive summary text on the page

> Starting from public Danish company-registry data alone, no CRM, no sales history, this model identifies the high-probability users of the target software product. Holdout AUC sits in the 0.74 to 0.78 range. The score is consumed downstream as a positive boost in the lead-scoring system.

## Refresh

Daily 06:00 CET via GitHub Actions. The workflow runs the prediction pipeline against the live warehouse, writes new scores to the `scores` table, and triggers a Power BI dataset refresh through the service.

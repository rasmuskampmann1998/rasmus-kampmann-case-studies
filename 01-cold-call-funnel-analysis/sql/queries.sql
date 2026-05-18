-- Portfolio Case Study #12 — Full Funnel Analytical Queries
-- Reads the dim/fact star schema. Postgres-flavored; adjust DATE_PART / EXTRACT as needed.

-- ============================================================
-- Q1. Funnel waterfall (top of funnel → won)
-- ============================================================
SELECT
    'Calls Attempted'      AS funnel_step, COUNT(*)                         AS records FROM fact_calls
UNION ALL SELECT
    'Calls Connected',      SUM(is_connected)                                FROM fact_calls
UNION ALL SELECT
    'Meetings Booked',      SUM(is_meeting_booked)                           FROM fact_calls
UNION ALL SELECT
    'Meetings Held',        COUNT(*) FILTER (WHERE meeting_status = 'Held')  FROM fact_meetings
UNION ALL SELECT
    'Deals Won',            SUM(is_won)                                      FROM fact_deals;

-- ============================================================
-- Q2. Conversion rates between adjacent steps
-- ============================================================
WITH s AS (
    SELECT
        (SELECT COUNT(*) FROM fact_calls)                                            AS calls,
        (SELECT SUM(is_connected) FROM fact_calls)                                   AS connected,
        (SELECT SUM(is_meeting_booked) FROM fact_calls)                              AS booked,
        (SELECT COUNT(*) FROM fact_meetings WHERE meeting_status = 'Held')           AS held,
        (SELECT SUM(is_won) FROM fact_deals)                                         AS won
)
SELECT
    ROUND(100.0 * connected / NULLIF(calls, 0), 2)      AS connect_rate_pct,
    ROUND(100.0 * booked    / NULLIF(connected, 0), 2)  AS meeting_book_rate_pct,
    ROUND(100.0 * held      / NULLIF(booked, 0), 2)     AS meeting_show_rate_pct,
    ROUND(100.0 * won       / NULLIF(held, 0), 2)       AS won_from_meeting_pct,
    ROUND(100.0 * won       / NULLIF(calls, 0), 2)      AS overall_win_rate_pct
FROM s;

-- ============================================================
-- Q3. Rep leaderboard (only reps with >= 50 calls)
-- ============================================================
SELECT
    r.rep_name,
    r.rep_team,
    COUNT(DISTINCT c.call_key)                                  AS total_calls,
    SUM(c.is_connected)                                         AS connected_calls,
    SUM(c.is_meeting_booked)                                    AS meetings_booked,
    COALESCE(SUM(d.is_won), 0)                                  AS deals_won,
    COALESCE(ROUND(SUM(d.mrr_usd) FILTER (WHERE d.is_won = 1)::NUMERIC, 0), 0) AS won_mrr_usd,
    ROUND(100.0 * SUM(c.is_meeting_booked) / NULLIF(COUNT(DISTINCT c.call_key), 0), 2) AS meeting_rate_pct
FROM dim_rep r
LEFT JOIN fact_calls c ON c.rep_key = r.rep_key
LEFT JOIN fact_deals d ON d.rep_key = r.rep_key
GROUP BY r.rep_name, r.rep_team
HAVING COUNT(DISTINCT c.call_key) >= 50
ORDER BY won_mrr_usd DESC;

-- ============================================================
-- Q4. Win rate by company industry
-- ============================================================
SELECT
    co.industry,
    COUNT(*)                                                  AS total_deals,
    SUM(d.is_won)                                             AS won,
    SUM(d.is_lost)                                            AS lost,
    ROUND(100.0 * SUM(d.is_won) / NULLIF(COUNT(*), 0), 2)     AS win_rate_pct,
    ROUND(AVG(d.mrr_usd) FILTER (WHERE d.is_won = 1)::NUMERIC, 2) AS avg_won_mrr_usd
FROM fact_deals d
JOIN dim_company co ON co.company_key = d.company_key
GROUP BY co.industry
ORDER BY win_rate_pct DESC;

-- ============================================================
-- Q5a. Win rate by employee band (THE primary ICP signal)
--      The 6-20 band is the sweet spot; everything else lags.
-- ============================================================
SELECT
    co.employee_band,
    COUNT(*)                                                  AS held_deals,
    SUM(d.is_won)                                             AS won,
    ROUND(100.0 * SUM(d.is_won) / NULLIF(COUNT(*), 0), 2)     AS win_rate_pct
FROM fact_deals d
JOIN dim_company  co ON co.company_key = d.company_key
JOIN fact_meetings m ON m.deal_key     = d.deal_key
WHERE m.meeting_status = 'Held'
GROUP BY co.employee_band
ORDER BY win_rate_pct DESC;

-- ============================================================
-- Q5b. Win rate by accounting system (the NON-signal control)
--      Every prospect already has a system, so this is flat by
--      design — kept as the "what doesn't predict" contrast.
-- ============================================================
SELECT
    co.accounting_system,
    COUNT(*)                                                  AS total_deals,
    SUM(d.is_won)                                             AS won,
    ROUND(100.0 * SUM(d.is_won) / NULLIF(COUNT(*), 0), 2)     AS win_rate_pct
FROM fact_deals d
JOIN dim_company co ON co.company_key = d.company_key
GROUP BY co.accounting_system
ORDER BY win_rate_pct DESC;

-- ============================================================
-- Q6. Lost-reason Pareto
-- ============================================================
SELECT
    lr.reason_category,
    lr.lost_reason,
    COUNT(*) AS lost_deals,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_losses
FROM fact_deals d
JOIN dim_lost_reason lr ON lr.lost_reason_key = d.lost_reason_key
WHERE d.is_lost = 1
GROUP BY lr.reason_category, lr.lost_reason
ORDER BY lost_deals DESC;

-- ============================================================
-- Q7. Velocity — call to meeting, meeting to close
-- ============================================================
SELECT
    'days_call_to_meeting'  AS metric,
    ROUND(AVG(days_from_create)::NUMERIC, 1) AS avg_days,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_from_create) AS median_days,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY days_from_create) AS p90_days
FROM fact_meetings WHERE days_from_create IS NOT NULL
UNION ALL SELECT
    'days_meeting_to_close',
    ROUND(AVG(days_to_close)::NUMERIC, 1),
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_close),
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY days_to_close)
FROM fact_meetings WHERE days_to_close IS NOT NULL;

-- ============================================================
-- Q8. Monthly won cohort
-- ============================================================
SELECT
    dt.year,
    dt.month,
    dt.month_name,
    COUNT(*)                                            AS won_deals,
    ROUND(SUM(d.mrr_usd)::NUMERIC, 0)                   AS won_mrr_usd,
    ROUND(AVG(d.deal_age_days)::NUMERIC, 1)             AS avg_cycle_days
FROM fact_deals d
JOIN dim_date dt ON dt.date_key = d.won_date_key
WHERE d.is_won = 1
GROUP BY dt.year, dt.month, dt.month_name
ORDER BY dt.year, dt.month;

-- ============================================================
-- Q9. Win rate heatmap — Industry × Employee Band
-- ============================================================
SELECT
    co.industry,
    co.employee_band,
    COUNT(*)                                              AS deals,
    ROUND(100.0 * SUM(d.is_won) / NULLIF(COUNT(*), 0), 1) AS win_rate_pct
FROM fact_deals d
JOIN dim_company co ON co.company_key = d.company_key
GROUP BY co.industry, co.employee_band
ORDER BY co.industry, co.employee_band;

-- ============================================================
-- Q10. Funnel drop-off by source
-- ============================================================
SELECT
    s.source_name,
    COUNT(*)                                              AS deals,
    SUM(CASE WHEN st.stage_order >= 3 THEN 1 ELSE 0 END)  AS reached_meeting,
    SUM(d.is_won)                                         AS won,
    ROUND(100.0 * SUM(d.is_won) / NULLIF(COUNT(*), 0), 1) AS win_rate_pct
FROM fact_deals d
JOIN dim_source s ON s.source_key = d.source_key
JOIN dim_stage  st ON st.stage_key = d.stage_key
GROUP BY s.source_name
ORDER BY win_rate_pct DESC;

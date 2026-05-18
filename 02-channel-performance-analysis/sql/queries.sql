-- Channel Performance — Analytical Queries
-- Reads the dim/fact star schema. Postgres-flavored; PERCENTILE_CONT and the
-- FILTER clause also run in DuckDB unchanged.

-- ============================================================
-- Q1. Channel performance scorecard (the headline table)
--     win rate, volume share, time-to-won, won MRR, MRR per dialer hour
-- ============================================================
select
    c.channel_name,
    c.channel_group,
    count(*)                                              as deals,
    sum(d.is_won)                                         as won,
    round(100.0 * sum(d.is_won) / count(*), 1)            as win_rate_pct,
    round(100.0 * count(*) / sum(count(*)) over (), 1)    as vol_share_pct,
    percentile_cont(0.5) within group (
        order by d.deal_age_days) filter (where d.is_won = 1) as t2w_median_days,
    sum(d.mrr_usd)                                        as won_mrr,
    round(sum(d.mrr_usd)
          / nullif(sum(d.dialer_hours_attributed), 0), 0) as mrr_per_dialer_hr
from fact_deals d
join dim_channel c on c.channel_key = d.channel_key
group by c.channel_name, c.channel_group
order by won_mrr desc;

-- ============================================================
-- Q2. Channel-group rollup — win rate and share of won MRR
-- ============================================================
with g as (
    select c.channel_group,
           count(*)        as deals,
           sum(d.is_won)   as won,
           sum(d.mrr_usd)  as won_mrr
    from fact_deals d
    join dim_channel c on c.channel_key = d.channel_key
    group by c.channel_group
)
select channel_group,
       round(100.0 * won / deals, 1)                          as win_rate_pct,
       won_mrr,
       round(100.0 * won_mrr / sum(won_mrr) over (), 1)        as won_mrr_share_pct
from g
order by win_rate_pct desc;

-- ============================================================
-- Q3. Channel economics — win, retention, and net revenue, all 10 channels
--     (Phase 8: was a 2-row dialer/non-dialer split. dialer_hours is non-zero
--     for only 2 of 10 channels, so that cut answered the resource question
--     but not "which channel is best". "Best" = wins AND the wins stay, so
--     this reports win rate, M12 logo retention, and NET won MRR per channel.
--     net_won_mrr = won MRR that did NOT churn within the 12-month window.)
-- ============================================================
select
    c.channel_name,
    c.channel_group,
    count(*)                                                  as deals,
    round(100.0 * sum(d.is_won) / count(*), 1)                as win_rate_pct,
    sum(d.is_won)                                             as won_deals,
    round(100.0 * (1.0 - sum(d.is_churned)
          / nullif(sum(d.is_won), 0)), 1)                     as m12_retention_pct,
    sum(d.mrr_usd) filter (where d.is_won = 1)                as won_mrr,
    sum(d.mrr_usd) filter (where d.is_won = 1)
      - sum(d.churned_mrr) filter (where d.is_won = 1)        as net_won_mrr,
    round(100.0 * (sum(d.mrr_usd) filter (where d.is_won = 1)
          - sum(d.churned_mrr) filter (where d.is_won = 1))
          / nullif(sum(d.mrr_usd) filter (where d.is_won = 1), 0), 1) as nrr_pct,
    sum(d.dialer_hours_attributed)                            as dialer_hours
-- NRR numerator/denominator are explicitly won-only via FILTER. mrr_usd and
-- churned_mrr are already 0 for lost deals by construction, so this does not
-- change the numbers — it makes the retention denominator auditable and
-- removes the latent risk if the generator ever assigns MRR to a lost deal.
from fact_deals d
join dim_channel c on c.channel_key = d.channel_key
group by c.channel_name, c.channel_group
order by net_won_mrr desc;

-- ============================================================
-- Q4. Time-to-won percentiles by channel (won deals only)
-- ============================================================
select
    c.channel_name,
    count(*)                                                          as won_deals,
    percentile_cont(0.25) within group (order by d.deal_age_days)      as p25_days,
    percentile_cont(0.50) within group (order by d.deal_age_days)      as median_days,
    percentile_cont(0.90) within group (order by d.deal_age_days)      as p90_days
from fact_deals d
join dim_channel c on c.channel_key = d.channel_key
where d.is_won = 1
group by c.channel_name
order by median_days;

-- ============================================================
-- Q5. The re-booking trap — dialer hours burned vs MRR returned
-- ============================================================
-- fact_meetings is pre-aggregated to one row per deal first. The generator
-- emits exactly one meeting per deal today, but joining the raw meeting grain
-- to the deal grain would silently overcount if that ever changes (fan-out).
with meeting_by_deal as (
    select
        deal_key,
        max(case when meeting_status = 'Cancelled' then 1 else 0 end) as any_cancelled
    from fact_meetings
    group by deal_key
)
select
    c.channel_name,
    count(*)                                                  as deals,
    round(100.0 * sum(d.is_won) / count(*), 1)                as win_rate_pct,
    round(100.0 * sum(mbd.any_cancelled) / count(*), 1)       as cancel_rate_pct,
    sum(d.dialer_hours_attributed)                            as dialer_hours,
    sum(d.mrr_usd)                                            as won_mrr
from fact_deals d
join dim_channel c       on c.channel_key = d.channel_key
join meeting_by_deal mbd on mbd.deal_key  = d.deal_key
where c.channel_name = 'Re-bookings'
group by c.channel_name;

-- ============================================================
-- Q6. Channel x employee band interaction (win-rate matrix)
-- ============================================================
select
    c.channel_name,
    co.employee_band,
    count(*)                                     as deals,
    round(100.0 * sum(d.is_won) / count(*), 1)   as win_rate_pct
from fact_deals d
join dim_channel c  on c.channel_key  = d.channel_key
join dim_company co on co.company_key = d.company_key
group by c.channel_name, co.employee_band
having count(*) >= 20
order by c.channel_name, co.employee_band;

-- ============================================================
-- Q7. Lost-reason Pareto by channel group
-- ============================================================
select
    c.channel_group,
    lr.reason_category,
    count(*)                                                          as losses,
    round(100.0 * count(*)
          / sum(count(*)) over (partition by c.channel_group), 1)     as pct_of_group_losses
from fact_deals d
join dim_channel c       on c.channel_key      = d.channel_key
join dim_lost_reason lr  on lr.lost_reason_key = d.lost_reason_key
where d.is_lost = 1
group by c.channel_group, lr.reason_category
order by c.channel_group, losses desc;

-- ============================================================
-- Q8. Acquisition vs expansion split
-- ============================================================
select
    case when c.channel_group = 'Expansion' then 'Expansion'
         else 'New acquisition' end               as motion,
    count(*)                                       as deals,
    sum(d.is_won)                                  as won,
    round(100.0 * sum(d.is_won) / count(*), 1)     as win_rate_pct,
    sum(d.mrr_usd)                                 as won_mrr
from fact_deals d
join dim_channel c on c.channel_key = d.channel_key
group by motion
order by won_mrr desc;

-- ============================================================
-- Q9. Channel retention & NRR — the post-sale axis (won deals only)
--     (Phase 8: replaced the monthly win-rate cohort query. created_date_key
--     is uniform-random in the generator — there is no designed time trend,
--     so a monthly cohort plotted noise and implied a finding that does not
--     exist. Retention IS a designed signal, so this is the query that earns
--     its place. won_n is reported so small-n channels (Re-bookings n=14,
--     Instagram, SEO) are read directionally, not to the decimal.)
-- ============================================================
select
    c.channel_name,
    sum(d.is_won)                                                   as won_n,
    sum(d.is_churned)                                               as churned_n,
    round(100.0 * (1.0 - sum(d.is_churned)
          / nullif(sum(d.is_won), 0)), 1)                           as m12_retention_pct,
    sum(d.mrr_usd)                                                  as won_mrr,
    sum(d.churned_mrr)                                              as churned_mrr,
    round(100.0 * (sum(d.mrr_usd) - sum(d.churned_mrr))
          / nullif(sum(d.mrr_usd), 0), 1)                           as nrr_pct,
    case when sum(d.is_won) < 50 then 'small n — directional'
         else '' end                                                as read_note
from fact_deals d
join dim_channel c on c.channel_key = d.channel_key
where d.is_won = 1
group by c.channel_name
order by m12_retention_pct desc;

-- ============================================================
-- Q10. Channel allocation scorecard band rollup
--      (Scale / Maintain / Cap / Kill — the deck Slide 10 deliverable)
-- ============================================================
-- Phase 8: the band rollup now also carries M12 logo retention and NET won
-- MRR share. The bands are unchanged — the point is that the retention axis
-- *corroborates* the existing allocation (Scale retains best, Cap/Kill bleed
-- post-sale), so Re-bookings lands in Kill on two independent axes, not one.
with band as (
    select d.deal_key,
           d.channel_key,
           d.mrr_usd,
           d.churned_mrr,
           d.is_won,
           d.is_churned,
           d.dialer_hours_attributed,
           case
             when c.channel_name in ('LinkedIn Outbound','Referral',
                                     'Inbound Sales','Cross-sell',
                                     'Upsell')                      then 'Scale'
             when c.channel_name in ('Facebook Ads','SEO',
                                     'Instagram Ads')               then 'Maintain'
             when c.channel_name = 'Cold Calling'                   then 'Cap'
             when c.channel_name = 'Re-bookings'                    then 'Kill'
           end as band
    from fact_deals d
    join dim_channel c on c.channel_key = d.channel_key
)
select
    band,
    count(*)                                                   as deals,
    round(100.0 * count(*) / sum(count(*)) over (), 1)         as deal_share_pct,
    round(100.0 * sum(mrr_usd)
          / sum(sum(mrr_usd)) over (), 1)                      as won_mrr_share_pct,
    round(100.0 * (1.0 - sum(is_churned)
          / nullif(sum(is_won), 0)), 1)                        as m12_retention_pct,
    round(100.0 * (sum(mrr_usd) - sum(churned_mrr))
          / sum(sum(mrr_usd) - sum(churned_mrr)) over (), 1)   as net_mrr_share_pct,
    round(100.0 * sum(dialer_hours_attributed)
          / sum(sum(dialer_hours_attributed)) over (), 1)      as dialer_hr_share_pct
from band
group by band
order by won_mrr_share_pct desc;

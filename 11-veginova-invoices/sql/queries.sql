-- Analytical queries behind the finance dashboard.
-- All logic on the invoice-line fact. Illustrative data; real numbers are confidential.

-- ── Q1: Revenue, COGS, contribution (the headline) ────────────────────────────
-- Contribution margin (Dækningsbidrag), NOT statutory profit: COGS is direct seed
-- cost only; overhead lives in the bookkeeping system, by design.
select
  sum(amount_dkk_expected)                                          as revenue_expected,
  sum(amount_dkk_confirmed)                                         as revenue_confirmed,
  sum(amount_dkk_expected) - sum(amount_dkk_confirmed)             as outstanding,
  sum(cost_dkk)                                                     as cogs,
  sum(amount_dkk_expected) - sum(cost_dkk)                         as contribution
from fin.fct_revenue;

-- ── Q2: Contribution margin per seed variety (seed sales only) ────────────────
-- The honest margin view: filter to real seed lines (is_seed_revenue), so non-product
-- lines (licenses, logistics) don't inflate the margin.
select
  p.variety_name,
  sum(r.amount_dkk_expected)                                        as revenue,
  sum(r.cost_dkk)                                                   as cogs,
  round( (sum(r.amount_dkk_expected) - sum(r.cost_dkk))
         / nullif(sum(r.amount_dkk_expected), 0) * 100, 1)          as contribution_margin_pct
from fin.fct_revenue r
join fin.dim_product p using (product_key)
where r.is_seed_revenue
group by p.variety_name
order by contribution_margin_pct asc;     -- thinnest margin first

-- ── Q3: Customer profitability (revenue vs contribution) ──────────────────────
-- Surfaces customers who are big on revenue but small on contribution (a mix issue).
select
  c.customer_name,
  sum(r.amount_dkk_expected)                                        as revenue,
  sum(r.amount_dkk_expected) - sum(r.cost_dkk)                     as contribution,
  rank() over (order by sum(r.amount_dkk_expected) desc)            as revenue_rank,
  rank() over (order by sum(r.amount_dkk_expected) - sum(r.cost_dkk) desc) as contribution_rank
from fin.fct_revenue r
join fin.dim_customer c using (customer_key)
group by c.customer_name
order by revenue_rank;

-- ── Q4: AR ageing (what's owed, how old) ──────────────────────────────────────
select
  sum(bucket_0_30)   as b_0_30,
  sum(bucket_31_60)  as b_31_60,
  sum(bucket_61_90)  as b_61_90,
  sum(bucket_90_plus) as b_90_plus,
  sum(outstanding_dkk) as total_outstanding
from fin.v_receivables;

-- ── Q5: Customer concentration of outstanding receivables ─────────────────────
-- Which customers hold most of the overdue cash (collection-priority list).
select c.customer_name, v.outstanding_dkk, v.bucket_90_plus
from fin.v_receivables v
join fin.dim_customer c using (customer_key)
order by v.outstanding_dkk desc
limit 10;

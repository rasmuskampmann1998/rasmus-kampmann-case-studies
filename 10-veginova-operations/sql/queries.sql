-- Analytical queries behind the operations dashboard.
-- The engine (ops.v_production_plan) does the work; these are the cuts the report shows.
-- Illustrative data; real client numbers are confidential.

-- ── Q1: The production plan (the main page) ───────────────────────────────────
-- What to produce, per variety, with the red/green warning light.
select product_key, variety_name, expected_sales, stock_on_hand, incoming,
       ending_stock, status, production_need
from ops.v_production_plan
order by production_need desc, ending_stock asc;

-- ── Q2: Headline counts (the KPI cards) ───────────────────────────────────────
-- Note: # red and # needing production differ on purpose. A variety can be red
-- (ending stock below the line) yet need zero production if it covers its own sales.
select
  round(sum(production_need))                  as total_to_produce,
  count(*) filter (where status = 'red')       as varieties_red,
  count(*) filter (where production_need > 0)  as varieties_needing_production
from ops.v_production_plan;

-- ── Q3: Forecast-channel reconciliation (a validation cut) ────────────────────
-- The sales channels must sum exactly to each variety's expected sales.
-- Any row returned here is a mismatch (expected: zero rows).
select vp.product_key, vp.expected_sales, coalesce(sum(fs.qty_1000), 0) as channel_sum
from ops.v_production_plan vp
left join ops.forecast_sales fs
  on fs.product_key = vp.product_key and fs.sales_year = vp.sales_year
group by vp.product_key, vp.expected_sales
having abs(vp.expected_sales - coalesce(sum(fs.qty_1000), 0)) > 0.05;

-- ── Q4: Snapshot history (plan-vs-actual, once snapshots accumulate) ──────────
-- Each commit is a dated row-set; this shows how a variety's plan moved over time.
select product_key, snapshot_date, expected_sales, ending_stock, production_need, status
from ops.fct_production_plan
order by product_key, snapshot_date;

-- ── Q5: At-risk varieties (the warning list) ──────────────────────────────────
-- Red varieties, ordered by how far below the line they sit. The ones that also
-- need production are the urgent ones given the one-year lead time.
select product_key, variety_name, ending_stock, red_threshold,
       production_need,
       case when production_need > 0 then 'produce now' else 'watch' end as action
from ops.v_production_plan vp
join ops.product_params using (product_key)
where status = 'red'
order by ending_stock asc;

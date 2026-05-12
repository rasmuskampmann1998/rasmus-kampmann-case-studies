-- ── Q1: Top-15 seed varieties by 12-month forecast volume ──────────────────
with f as (
  select seed_code, sum(forecast_qty) as fc_qty
  from european seed producer.forecast_24m
  where scenario = 'base'
    and period_yyyymm between to_char(now(), 'YYYYMM')::int
                          and to_char(now() + interval '12 months', 'YYYYMM')::int
  group by seed_code
)
select seed_code,
       fc_qty,
       round(100.0 * fc_qty / sum(fc_qty) over (), 1) as pct_of_total,
       round(100.0 * sum(fc_qty) over (order by fc_qty desc) / sum(fc_qty) over (), 1) as cumulative_pct
from f
order by fc_qty desc
limit 15;

-- ── Q2: Inventory cover (months of stock at current sell-through) ──────────
with sell as (
  select seed_code, sum(qty) / 3.0 as monthly_sales
  from european seed producer.sales_orders
  where order_date >= now() - interval '90 days'
  group by seed_code
),
stock as (
  select seed_code, sum(qty_on_hand) as on_hand
  from european seed producer.inventory_log
  where last_count_date >= now() - interval '14 days'
  group by seed_code
)
select s.seed_code,
       stock.on_hand,
       s.monthly_sales,
       round(stock.on_hand / nullif(s.monthly_sales, 0), 1) as months_of_cover,
       case
         when stock.on_hand / nullif(s.monthly_sales, 0) < 2  then 'RED'
         when stock.on_hand / nullif(s.monthly_sales, 0) < 6  then 'AMBER'
         else 'GREEN'
       end as cover_band
from sell s
join stock using (seed_code)
order by months_of_cover nulls last;

-- ── Q3: Production vs. delivery-window mismatch ────────────────────────────
-- Flags seeds where production is scheduled to finish AFTER the contracted
-- delivery window opens, a recurring late-shipment risk.
with prod as (
  select seed_code,
         min(to_date(period_yyyymm::text, 'YYYYMM')) as production_finish
  from european seed producer.production_plan
  where status in ('planned', 'in_progress')
  group by seed_code
),
deliv as (
  select seed_code, min(delivery_window_from) as next_delivery
  from european seed producer.sales_orders
  where delivery_window_from >= current_date
  group by seed_code
)
select p.seed_code,
       p.production_finish,
       d.next_delivery,
       (p.production_finish - d.next_delivery) as days_late
from prod p
join deliv d using (seed_code)
where p.production_finish > d.next_delivery
order by days_late desc;

-- ── Q4: Raw-material intake by month (the "intake cliff") ──────────────────
select to_char(date_trunc('month', last_count_date), 'YYYY-MM') as month,
       sum(qty_on_hand) as intake_kg
from european seed producer.inventory_log
where last_count_date >= now() - interval '24 months'
group by 1
order by 1;

-- ── Q5: Forecast accuracy (MAPE, last 6 months) ────────────────────────────
with actuals as (
  select seed_code,
         to_char(date_trunc('month', order_date), 'YYYYMM')::int as period_yyyymm,
         sum(qty) as actual_qty
  from european seed producer.sales_orders
  where order_date >= now() - interval '6 months'
  group by 1, 2
),
forecast as (
  select seed_code, period_yyyymm, forecast_qty
  from european seed producer.forecast_24m
  where scenario = 'base'
    and forecast_run < now() - interval '6 months'
)
select round(avg(abs(a.actual_qty - f.forecast_qty) / nullif(a.actual_qty, 0)) * 100, 1) as mape_pct
from actuals a
join forecast f using (seed_code, period_yyyymm);

-- Operations / production-planning schema. Supabase / PostgreSQL flavour.
-- All variety codes and quantities in the public extracts are illustrative stand-ins.
--
-- The principle: ALL planning logic lives here, in SQL. Power BI renders the marts
-- and runs nothing of consequence. A production plan is stateful and has to recompute
-- the instant sales or stock change, so the engine is a view, not a DAX measure.

create schema if not exists ops;

-- ── Inputs (the planner's tables, refreshed from the warehouse / planning sheet) ──

-- Per-variety parameters: the safety red line and (when seeded) the production buffer.
create table if not exists ops.product_params (
  product_key    text primary key,           -- illustrative: VAR-A, VAR-B, ...
  variety_name   text,
  active         boolean not null default true,
  red_threshold  numeric not null default 100,  -- the "red line" (KS); colours the warning light
  safety_floor   numeric,                        -- production buffer floor (UNSEEDED in this version)
  safety_months  numeric                         -- months-of-cover buffer  (UNSEEDED in this version)
);

-- Expected sales per variety per sales year (sum of the forecast channels).
create table if not exists ops.forecast_sales (
  product_key  text not null,
  sales_year   text not null,             -- e.g. '26/27'
  channel      text not null,             -- the two sales channels that sum to expected_sales
  qty_1000     numeric not null,
  primary key (product_key, sales_year, channel)
);

-- Physical stock on hand, refreshed from the warehouse sheet (see python/).
create table if not exists ops.stock_on_hand (
  product_key  text not null,
  as_of_date   date not null,
  qty_1000     numeric not null,
  source       text default 'warehouse_sheet',
  primary key (product_key, as_of_date)
);

-- Seed already on the way (in production / shipping), net of waste.
create table if not exists ops.incoming_production (
  product_key  text not null,
  arrival_date date,
  qty_1000     numeric not null,
  primary key (product_key, arrival_date)
);

-- ── The engine: one view computes the whole plan ──────────────────────────────
-- production_need = produce-to-safety, floored at zero.
-- ending_stock    = stock + incoming - expected_sales.
-- status          = red when ending stock falls below the red line, else green.
create or replace view ops.v_production_plan as
with sales as (
  select product_key, sales_year, sum(qty_1000) as expected_sales
  from ops.forecast_sales group by product_key, sales_year
),
stock as (  -- latest snapshot per variety
  select distinct on (product_key) product_key, qty_1000 as stock_on_hand
  from ops.stock_on_hand order by product_key, as_of_date desc
),
inc as (
  select product_key, sum(qty_1000) as incoming
  from ops.incoming_production group by product_key
),
params as (
  select product_key, variety_name, active, red_threshold,
         -- production buffer: GREATEST(floor, months * sales/12); 0 while unseeded
         coalesce(greatest(safety_floor, 0), 0) as prod_safety
  from ops.product_params
)
select
  p.product_key,
  p.variety_name,
  s.sales_year,
  coalesce(s.expected_sales, 0)                                        as expected_sales,
  coalesce(st.stock_on_hand, 0)                                        as stock_on_hand,
  coalesce(i.incoming, 0)                                              as incoming,
  greatest(p.prod_safety + coalesce(s.expected_sales,0)
           - coalesce(st.stock_on_hand,0) - coalesce(i.incoming,0), 0) as production_need,
  coalesce(st.stock_on_hand,0) + coalesce(i.incoming,0)
           - coalesce(s.expected_sales,0)                              as ending_stock,
  case
    when not p.active then 'stopped'
    when coalesce(st.stock_on_hand,0) + coalesce(i.incoming,0)
         - coalesce(s.expected_sales,0) < p.red_threshold then 'red'
    else 'green'
  end                                                                  as status
from params p
left join sales s on s.product_key = p.product_key
left join stock st on st.product_key = p.product_key
left join inc   i  on i.product_key  = p.product_key
where coalesce(p.active, true);

-- ── The snapshot mechanism ────────────────────────────────────────────────────
-- A committed plan is frozen as a dated snapshot. Changing an input and committing
-- again writes a NEW snapshot rather than overwriting history, which is what makes
-- plan-vs-actual tracking possible later.
create table if not exists ops.fct_production_plan (
  snapshot_id    bigserial primary key,
  snapshot_date  date not null default current_date,
  product_key    text not null,
  sales_year     text,
  expected_sales numeric,
  stock_on_hand  numeric,
  incoming       numeric,
  production_need numeric,
  ending_stock   numeric,
  status         text,
  action         text,
  committed_by   text
);

create or replace function ops.commit_production_plan(p_by text default 'system')
returns void language sql as $$
  insert into ops.fct_production_plan
    (product_key, sales_year, expected_sales, stock_on_hand, incoming,
     production_need, ending_stock, status, action, committed_by)
  select product_key, sales_year, expected_sales, stock_on_hand, incoming,
         production_need, ending_stock, status, action, p_by
  from ops.v_production_plan;
$$;

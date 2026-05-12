-- ── Q1: AR ageing summary ──────────────────────────────────────────────────
select bucket,
       sum(amount) as outstanding_eur,
       count(*) as invoice_count
from (
  select case
           when days_overdue between 0 and 30   then '0–30'
           when days_overdue between 31 and 60  then '31–60'
           when days_overdue between 61 and 90  then '61–90'
           else '90+' end as bucket,
         outstanding_eur as amount
  from european seed producer_fin.invoice_status
  where derived_status = 'overdue'
) x
group by bucket
order by min(case when bucket = '0–30' then 1
                  when bucket = '31–60' then 2
                  when bucket = '61–90' then 3 else 4 end);

-- ── Q2: Top-10 overdue customers ──────────────────────────────────────────
select customer_id,
       sum(outstanding_eur) as overdue_eur,
       count(*) as overdue_invoices,
       max(days_overdue) as oldest_overdue_days
from european seed producer_fin.invoice_status
where derived_status = 'overdue'
group by customer_id
order by overdue_eur desc
limit 10;

-- ── Q3: Gross margin per seed variety ─────────────────────────────────────
with sales as (
  select o.seed_code,
         sum(o.qty) as kg_sold,
         sum(o.qty * (i.amount_eur / nullif(o.qty, 0))) as revenue_eur
  from european seed producer.sales_orders o
  join european seed producer_fin.invoices i on i.order_id = o.order_id
  where o.order_date >= now() - interval '12 months'
  group by o.seed_code
),
cost as (
  select seed_code, avg(cost_per_kg_eur) as avg_cost_per_kg
  from european seed producer_fin.production_cost
  where period_yyyymm >= to_char(now() - interval '12 months', 'YYYYMM')::int
  group by seed_code
)
select s.seed_code,
       s.kg_sold,
       s.revenue_eur,
       round(s.revenue_eur / nullif(s.kg_sold, 0), 2) as avg_price_per_kg,
       c.avg_cost_per_kg,
       round((s.revenue_eur - s.kg_sold * c.avg_cost_per_kg) / nullif(s.revenue_eur, 0) * 100, 1) as gross_margin_pct
from sales s
left join cost c using (seed_code)
order by gross_margin_pct asc;          -- thinnest margin first

-- ── Q4: DSO (days sales outstanding) ───────────────────────────────────────
select round(avg(extract(day from (payment_date - issue_date))), 1) as dso_days
from european seed producer_fin.invoices i
join european seed producer_fin.payments p using (invoice_no)
where i.issue_date >= now() - interval '12 months';

-- ── Q5: Customer profitability. revenue rank vs. gross-profit rank ────────
with rev as (
  select i.customer_id, sum(i.amount_eur) as revenue_eur
  from european seed producer_fin.invoices i
  where i.issue_date >= now() - interval '12 months'
  group by i.customer_id
),
gp as (
  select o.customer_id,
         sum((i.amount_eur / nullif(o.qty, 0) - c.cost_per_kg_eur) * o.qty) as gross_profit_eur
  from european seed producer.sales_orders o
  join european seed producer_fin.invoices i on i.order_id = o.order_id
  join european seed producer_fin.production_cost c
       on c.seed_code = o.seed_code
       and c.period_yyyymm = to_char(o.order_date, 'YYYYMM')::int
  where o.order_date >= now() - interval '12 months'
  group by o.customer_id
)
select r.customer_id,
       r.revenue_eur,
       gp.gross_profit_eur,
       rank() over (order by r.revenue_eur desc) as revenue_rank,
       rank() over (order by gp.gross_profit_eur desc) as gp_rank
from rev r
join gp using (customer_id)
order by revenue_rank;

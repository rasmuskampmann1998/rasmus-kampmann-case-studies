-- A European seed producer invoices + finance warehouse extension
-- Lives in the same Supabase instance as the operations schema.

create schema if not exists european seed producer_fin;

create table european seed producer_fin.invoices (
  invoice_no      text primary key,
  customer_id     text not null,
  order_id        bigint,
  issue_date      date not null,
  due_date        date not null,
  amount_eur      numeric(12,2) not null,
  status          text not null,           -- open / paid / overdue / disputed
  currency        text default 'EUR',
  created_at      timestamptz default now()
);
create index on european seed producer_fin.invoices (customer_id);
create index on european seed producer_fin.invoices (status, due_date);

create table european seed producer_fin.payments (
  payment_id      bigserial primary key,
  invoice_no      text not null references european seed producer_fin.invoices(invoice_no),
  payment_date    date not null,
  amount_eur      numeric(12,2) not null,
  method          text,                    -- bank / card / sepa / other
  loaded_at       timestamptz default now()
);
create index on european seed producer_fin.payments (invoice_no);
create index on european seed producer_fin.payments (payment_date);

create table european seed producer_fin.production_cost (
  seed_code       text not null,
  period_yyyymm   integer not null,
  cost_per_kg_eur numeric(10,4) not null,
  yield_factor    numeric(6,4) not null,   -- actual / theoretical
  loaded_at       timestamptz default now(),
  primary key (seed_code, period_yyyymm)
);

-- ── Views ──────────────────────────────────────────────────────────────────
create or replace view european seed producer_fin.invoice_status as
  with paid as (
    select invoice_no, coalesce(sum(amount_eur), 0) as paid_eur
    from european seed producer_fin.payments
    group by invoice_no
  )
  select i.invoice_no,
         i.customer_id,
         i.issue_date,
         i.due_date,
         i.amount_eur,
         coalesce(p.paid_eur, 0) as paid_eur,
         i.amount_eur - coalesce(p.paid_eur, 0) as outstanding_eur,
         case
           when i.amount_eur - coalesce(p.paid_eur, 0) <= 0 then 'paid'
           when i.due_date < current_date then 'overdue'
           else 'open'
         end as derived_status,
         greatest(current_date - i.due_date, 0) as days_overdue
  from european seed producer_fin.invoices i
  left join paid p using (invoice_no);

create or replace view european seed producer_fin.ar_ageing_buckets as
  select customer_id,
         sum(case when days_overdue between 0 and 30   then outstanding_eur else 0 end) as bucket_0_30,
         sum(case when days_overdue between 31 and 60  then outstanding_eur else 0 end) as bucket_31_60,
         sum(case when days_overdue between 61 and 90  then outstanding_eur else 0 end) as bucket_61_90,
         sum(case when days_overdue > 90               then outstanding_eur else 0 end) as bucket_90_plus,
         sum(outstanding_eur) as total_outstanding
  from european seed producer_fin.invoice_status
  where derived_status = 'overdue'
  group by customer_id;

-- A European seed producer operations warehouse. Supabase / PostgreSQL flavour
-- All customer/seed identifiers are anonymised in the public extracts.

create schema if not exists european seed producer;

create table european seed producer.sales_orders (
  order_id        bigint primary key,
  order_date      date not null,
  customer_id     text not null,            -- anonymised: Customer_NNNNN
  seed_code       text not null,            -- anonymised: SEED_NNNN
  qty             numeric(12,2) not null,
  unit            text not null default 'kg',
  delivery_window_from date,
  delivery_window_to   date,
  region          text,
  channel         text,                     -- direct / distributor / online
  created_at      timestamptz default now()
);
create index on european seed producer.sales_orders (seed_code, order_date);
create index on european seed producer.sales_orders (customer_id);

create table european seed producer.inventory_log (
  log_id          bigserial primary key,
  seed_code       text not null,
  lot_id          text not null,
  qty_on_hand     numeric(12,2) not null,
  unit            text not null default 'kg',
  location        text,
  last_count_date date not null,
  loaded_at       timestamptz default now()
);
create index on european seed producer.inventory_log (seed_code, last_count_date);

create table european seed producer.production_plan (
  plan_id         bigserial primary key,
  seed_code       text not null,
  period_yyyymm   integer not null,
  planned_qty     numeric(12,2) not null,
  status          text not null,            -- planned / in_progress / done / paused
  scenario        text not null default 'base',
  loaded_at       timestamptz default now()
);
create unique index on european seed producer.production_plan (seed_code, period_yyyymm, scenario);

create table european seed producer.forecast_24m (
  forecast_id     bigserial primary key,
  seed_code       text not null,
  period_yyyymm   integer not null,
  forecast_qty    numeric(12,2) not null,
  scenario        text not null,            -- base / upside / downside
  forecast_run    date not null,
  loaded_at       timestamptz default now()
);
create index on european seed producer.forecast_24m (seed_code, period_yyyymm, scenario);

-- Dimension tables (joined views)
create or replace view european seed producer.dim_seed as
  select distinct seed_code from european seed producer.sales_orders
  union
  select distinct seed_code from european seed producer.inventory_log
  union
  select distinct seed_code from european seed producer.production_plan
  union
  select distinct seed_code from european seed producer.forecast_24m;

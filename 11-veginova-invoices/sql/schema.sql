-- Invoice & finance star schema. Supabase / PostgreSQL flavour.
-- All customer/invoice/product identifiers and amounts are illustrative stand-ins.
--
-- The principle: invoices are the source of truth, reconciled to the ledger. The
-- logic lives in SQL; Power BI renders the mart and aggregates, nothing more.
-- Grain of the fact table is the INVOICE LINE (one row per line on one invoice).

create schema if not exists fin;

-- ── Dimensions ────────────────────────────────────────────────────────────────
create table if not exists fin.dim_date (
  date_key date primary key,
  year     int,
  month    int,
  quarter  int
);

create table if not exists fin.dim_customer (
  customer_key text primary key,        -- illustrative: CUST-001 ...
  customer_name text,
  country      text
);

create table if not exists fin.dim_product (
  product_key  text primary key,         -- illustrative variety code
  variety_name text,
  is_seed      boolean default true
);

-- Revenue classification (Product, R&D, Earn-out, Recharge, Other). COGS only hits Product.
create table if not exists fin.dim_bucket (
  bucket_key      text primary key,
  is_seed_revenue boolean default false
);

-- Disconnected slicer: drives the revenue-basis toggle. No relationship to the fact.
create table if not exists fin.ref_revenue_basis (
  basis text primary key                 -- 'Expected' | 'Confirmed' | 'Recognized'
);

-- ── Fact (invoice-line grain) ──────────────────────────────────────────────────
create table if not exists fin.fct_revenue (
  invoice_no            text,
  line_id               bigint,
  date_key              date references fin.dim_date(date_key),
  recognition_date      date references fin.dim_date(date_key),  -- inactive relationship in the model
  customer_key          text references fin.dim_customer(customer_key),
  product_key           text references fin.dim_product(product_key),
  bucket_key            text references fin.dim_bucket(bucket_key),
  amount_dkk_expected   numeric,   -- invoiced (the default basis)
  amount_dkk_confirmed  numeric,   -- paid / cash basis (= expected when paid, else 0)
  cost_dkk              numeric,   -- direct seed cost (Product bucket only)
  qty_1000              numeric,
  is_seed_revenue       boolean,
  line_type             text,      -- NULL = real seed line; else License/Logistics/etc.
  primary key (invoice_no, line_id)
);
create index if not exists ix_fct_revenue_date on fin.fct_revenue (date_key);
create index if not exists ix_fct_revenue_cust on fin.fct_revenue (customer_key);

-- ── Receivables view (AR ageing) ───────────────────────────────────────────────
-- Outstanding = expected - confirmed, bucketed by age of the unpaid amount.
create or replace view fin.v_receivables as
select
  customer_key,
  sum(amount_dkk_expected - amount_dkk_confirmed) as outstanding_dkk,
  sum(case when current_date - date_key between 0 and 30  then amount_dkk_expected - amount_dkk_confirmed else 0 end) as bucket_0_30,
  sum(case when current_date - date_key between 31 and 60 then amount_dkk_expected - amount_dkk_confirmed else 0 end) as bucket_31_60,
  sum(case when current_date - date_key between 61 and 90 then amount_dkk_expected - amount_dkk_confirmed else 0 end) as bucket_61_90,
  sum(case when current_date - date_key > 90             then amount_dkk_expected - amount_dkk_confirmed else 0 end) as bucket_90_plus
from fin.fct_revenue
where amount_dkk_expected - amount_dkk_confirmed > 0
group by customer_key;

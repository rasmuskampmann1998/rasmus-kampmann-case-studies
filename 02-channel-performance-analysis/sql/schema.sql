-- Channel Performance Analysis — Star Schema
-- Postgres-flavored DDL. Adjust types lightly for SQL Server / DuckDB / Snowflake.
--
-- Question: across acquisition channels, which produces the most won revenue
-- fastest, and where is dialer time being spent that doesn't return?
--
-- Grain:
--   fact_deals    — one row per deal (channel-attributed)
--   fact_touches  — one row per acquisition touch (first-touch / cost)
--   fact_meetings — one row per booked meeting

drop table if exists fact_meetings cascade;
drop table if exists fact_deals    cascade;
drop table if exists fact_touches  cascade;
drop table if exists dim_date         cascade;
drop table if exists dim_company      cascade;
drop table if exists dim_rep          cascade;
drop table if exists dim_campaign     cascade;
drop table if exists dim_stage        cascade;
drop table if exists dim_lost_reason  cascade;
drop table if exists dim_channel      cascade;

-- ============================================================
-- DIMENSIONS
-- ============================================================

create table dim_date (
    date_key         integer primary key,           -- YYYYMMDD
    date             date        not null,
    year             smallint    not null,
    quarter          smallint    not null,
    month            smallint    not null,
    month_name       varchar(12) not null,
    week_of_year     smallint    not null,
    day_of_week      varchar(12) not null,
    is_business_day  boolean     not null
);
create index idx_dim_date_date    on dim_date(date);
create index idx_dim_date_yearmth on dim_date(year, month);

-- dim_channel is the PRIMARY analytical dimension. channel_group rolls
-- individual channels into the five acquisition motions; is_dialer_motion
-- flags the channels that consume sales-dialer capacity (the scarce resource
-- the headline metric — won MRR per dialer hour — is measured against).
create table dim_channel (
    channel_key       varchar(6)   primary key,
    channel_name      varchar(40)  not null,
    channel_group     varchar(20)  not null,  -- Outbound / Inbound / Paid / Expansion / Referral
    is_dialer_motion  smallint     not null,  -- 1 = consumes dialer hours
    cost_model        varchar(20)  not null   -- per-dial / per-lead / CPM / zero
);

-- dim_campaign.channel_key is a documented reference only. In the Power BI
-- model it is intentionally NOT joined to dim_channel (that would snowflake
-- the schema). Channel context on a campaign comes through fact_deals, not
-- through this column.
create table dim_campaign (
    campaign_key   varchar(8)   primary key,
    campaign_name  varchar(80)  not null,
    channel_key    varchar(6)   not null references dim_channel(channel_key),
    segment        varchar(20)  not null,
    launch_date    date         not null
);

create table dim_company (
    company_key       varchar(10)  primary key,
    company_name      varchar(120) not null,
    industry          varchar(40)  not null,
    employee_band     varchar(10)  not null,
    revenue_band_usd  varchar(20)  not null,
    region            varchar(20)  not null,
    company_form      varchar(30)  not null,
    company_age_band  varchar(10)  not null
);
create index idx_dim_company_industry on dim_company(industry);
create index idx_dim_company_empband  on dim_company(employee_band);

create table dim_rep (
    rep_key       varchar(6)   primary key,
    rep_name      varchar(80)  not null,
    rep_team      varchar(40)  not null,
    tenure_band   varchar(6)   not null
);

create table dim_stage (
    stage_key    varchar(6)   primary key,
    stage_name   varchar(40)  not null,
    stage_order  smallint     not null,
    funnel_step  varchar(20)  not null    -- Lead / Meeting / Negotiation / Close
);

create table dim_lost_reason (
    lost_reason_key   varchar(6)   primary key,
    lost_reason       varchar(60)  not null,
    reason_category   varchar(20)  not null  -- Fit / Price / Timing / Competitor / No-response / Other / Unknown
);

-- ============================================================
-- FACTS
-- ============================================================

-- One acquisition touch per row. Used for first-touch attribution and the
-- dialer-cost rollup (touch_dialer_minutes is 0 for non-dialer channels).
create table fact_touches (
    touch_key            varchar(14) primary key,
    company_key          varchar(10) not null references dim_company(company_key),
    channel_key          varchar(6)  not null references dim_channel(channel_key),
    rep_key              varchar(6)  not null references dim_rep(rep_key),
    touch_date_key       integer     not null references dim_date(date_key),
    touch_outcome        varchar(30) not null,
    touch_dialer_minutes integer     not null,   -- 0 for non-dialer channels
    led_to_deal          smallint    not null
);
create index idx_fact_touches_company on fact_touches(company_key);
create index idx_fact_touches_channel on fact_touches(channel_key);
create index idx_fact_touches_date    on fact_touches(touch_date_key);

create table fact_deals (
    deal_key                 varchar(10)  primary key,
    company_key              varchar(10)  not null references dim_company(company_key),
    channel_key              varchar(6)   not null references dim_channel(channel_key),
    campaign_key             varchar(8)   references dim_campaign(campaign_key),
    rep_key                  varchar(6)   not null references dim_rep(rep_key),
    stage_key                varchar(6)   not null references dim_stage(stage_key),
    lost_reason_key          varchar(6)   references dim_lost_reason(lost_reason_key),
    created_date_key         integer      not null references dim_date(date_key),
    won_date_key             integer      references dim_date(date_key),
    lost_date_key            integer      references dim_date(date_key),
    mrr_usd                  numeric(12,2) not null default 0,
    tcv_usd                  numeric(12,2) not null default 0,
    dialer_hours_attributed  numeric(8,2)  not null default 0,  -- 0 for non-dialer channels
    deal_age_days            integer,
    is_won                   smallint     not null,
    is_lost                  smallint     not null,
    -- Post-won lifecycle (only meaningful when is_won = 1). A won customer
    -- that later cancels is the only thing that can express channel CHURN —
    -- the acquisition funnel above stops at the close line and cannot.
    churn_date_key           integer      references dim_date(date_key),  -- 0 if never churned / not won
    is_churned               smallint     not null default 0,             -- 1 = a won deal that cancelled within the window
    retained_months          integer,                                     -- months the won customer stayed active (NULL if not won)
    churned_mrr              numeric(12,2) not null default 0              -- mrr_usd of the deal if is_churned else 0
);
create index idx_fact_deals_company on fact_deals(company_key);
create index idx_fact_deals_channel on fact_deals(channel_key);
create index idx_fact_deals_rep     on fact_deals(rep_key);
create index idx_fact_deals_stage   on fact_deals(stage_key);
create index idx_fact_deals_created on fact_deals(created_date_key);
create index idx_fact_deals_won     on fact_deals(won_date_key);
create index idx_fact_deals_churn   on fact_deals(churn_date_key);

create table fact_meetings (
    meeting_key            varchar(10) primary key,
    deal_key               varchar(10) not null,
    company_key            varchar(10) not null references dim_company(company_key),
    channel_key            varchar(6)  not null references dim_channel(channel_key),
    rep_key                varchar(6)  not null references dim_rep(rep_key),
    meeting_date_key       integer     not null references dim_date(date_key),
    meeting_status         varchar(20) not null,
    no_show_flag           smallint    not null,
    days_from_first_touch  integer,
    days_to_close          integer
);
create index idx_fact_meetings_company on fact_meetings(company_key);
create index idx_fact_meetings_channel on fact_meetings(channel_key);
create index idx_fact_meetings_date    on fact_meetings(meeting_date_key);
create index idx_fact_meetings_deal    on fact_meetings(deal_key);

-- ============================================================
-- LOAD HINT (Postgres)
-- After running this DDL, load the CSVs:
--   \copy dim_date         FROM 'data/dim_date.csv'         CSV HEADER;
--   \copy dim_channel      FROM 'data/dim_channel.csv'      CSV HEADER;
--   \copy dim_campaign     FROM 'data/dim_campaign.csv'     CSV HEADER;
--   \copy dim_company      FROM 'data/dim_company.csv'      CSV HEADER;
--   \copy dim_rep          FROM 'data/dim_rep.csv'          CSV HEADER;
--   \copy dim_stage        FROM 'data/dim_stage.csv'        CSV HEADER;
--   \copy dim_lost_reason  FROM 'data/dim_lost_reason.csv'  CSV HEADER;
--   \copy fact_touches     FROM 'data/fact_touches.csv'     CSV HEADER;
--   \copy fact_deals       FROM 'data/fact_deals.csv'       CSV HEADER;
--   \copy fact_meetings    FROM 'data/fact_meetings.csv'    CSV HEADER;
-- ============================================================

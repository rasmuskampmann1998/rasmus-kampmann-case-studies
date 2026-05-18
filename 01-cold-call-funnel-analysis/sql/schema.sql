-- Portfolio Case Study #12 — Full Funnel Star Schema
-- Postgres-flavored DDL. Adjust types lightly for SQL Server / DuckDB / Snowflake.

DROP TABLE IF EXISTS fact_meetings CASCADE;
DROP TABLE IF EXISTS fact_deals    CASCADE;
DROP TABLE IF EXISTS fact_calls    CASCADE;
DROP TABLE IF EXISTS dim_date         CASCADE;
DROP TABLE IF EXISTS dim_company      CASCADE;
DROP TABLE IF EXISTS dim_rep          CASCADE;
DROP TABLE IF EXISTS dim_campaign     CASCADE;
DROP TABLE IF EXISTS dim_stage        CASCADE;
DROP TABLE IF EXISTS dim_lost_reason  CASCADE;
DROP TABLE IF EXISTS dim_source       CASCADE;

-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE dim_date (
    date_key         INTEGER PRIMARY KEY,           -- YYYYMMDD
    date             DATE        NOT NULL,
    year             SMALLINT    NOT NULL,
    quarter          SMALLINT    NOT NULL,
    month            SMALLINT    NOT NULL,
    month_name       VARCHAR(12) NOT NULL,
    week_of_year     SMALLINT    NOT NULL,
    day_of_week      VARCHAR(12) NOT NULL,
    is_business_day  BOOLEAN     NOT NULL
);
CREATE INDEX idx_dim_date_date    ON dim_date(date);
CREATE INDEX idx_dim_date_yearmth ON dim_date(year, month);

CREATE TABLE dim_company (
    company_key       VARCHAR(10)  PRIMARY KEY,
    company_name      VARCHAR(120) NOT NULL,
    industry          VARCHAR(40)  NOT NULL,
    employee_band     VARCHAR(10)  NOT NULL,
    revenue_band_usd  VARCHAR(20)  NOT NULL,
    region            VARCHAR(20)  NOT NULL,
    accounting_system VARCHAR(30)  NOT NULL,
    company_type      VARCHAR(30)  NOT NULL,
    company_age_band  VARCHAR(10)  NOT NULL
);
CREATE INDEX idx_dim_company_industry ON dim_company(industry);
CREATE INDEX idx_dim_company_region   ON dim_company(region);
CREATE INDEX idx_dim_company_empband  ON dim_company(employee_band);

CREATE TABLE dim_rep (
    rep_key       VARCHAR(6)   PRIMARY KEY,
    rep_name      VARCHAR(80)  NOT NULL,
    rep_team      VARCHAR(40)  NOT NULL,
    tenure_band   VARCHAR(6)   NOT NULL
);

CREATE TABLE dim_campaign (
    campaign_key   VARCHAR(8)   PRIMARY KEY,
    campaign_name  VARCHAR(80)  NOT NULL,
    segment        VARCHAR(20)  NOT NULL,
    launch_date    DATE         NOT NULL
);

CREATE TABLE dim_stage (
    stage_key    VARCHAR(6)   PRIMARY KEY,
    stage_name   VARCHAR(40)  NOT NULL,
    stage_order  SMALLINT     NOT NULL,
    funnel_step  VARCHAR(20)  NOT NULL    -- Attempt / Connect / Meeting / Negotiation / Close
);

CREATE TABLE dim_lost_reason (
    lost_reason_key   VARCHAR(6)   PRIMARY KEY,
    lost_reason       VARCHAR(60)  NOT NULL,
    reason_category   VARCHAR(20)  NOT NULL  -- Fit / Price / Timing / Competitor / No-response / Other / Unknown
);

CREATE TABLE dim_source (
    source_key   VARCHAR(8)   PRIMARY KEY,
    source_name  VARCHAR(30)  NOT NULL,
    channel      VARCHAR(20)  NOT NULL
);

-- ============================================================
-- FACTS
-- ============================================================

CREATE TABLE fact_calls (
    call_key           VARCHAR(14) PRIMARY KEY,
    company_key        VARCHAR(10) NOT NULL REFERENCES dim_company(company_key),
    rep_key            VARCHAR(6)  NOT NULL REFERENCES dim_rep(rep_key),
    call_date_key      INTEGER     NOT NULL REFERENCES dim_date(date_key),
    call_outcome       VARCHAR(30) NOT NULL,
    attempts_count     INTEGER     NOT NULL,
    call_duration_sec  INTEGER     NOT NULL,
    is_connected       SMALLINT    NOT NULL,
    is_meeting_booked  SMALLINT    NOT NULL
);
CREATE INDEX idx_fact_calls_company ON fact_calls(company_key);
CREATE INDEX idx_fact_calls_rep     ON fact_calls(rep_key);
CREATE INDEX idx_fact_calls_date    ON fact_calls(call_date_key);
CREATE INDEX idx_fact_calls_outcome ON fact_calls(call_outcome);

CREATE TABLE fact_meetings (
    meeting_key        VARCHAR(10) PRIMARY KEY,
    deal_key           VARCHAR(10) NOT NULL,
    company_key        VARCHAR(10) NOT NULL REFERENCES dim_company(company_key),
    rep_key            VARCHAR(6)  NOT NULL REFERENCES dim_rep(rep_key),
    meeting_date_key   INTEGER     NOT NULL REFERENCES dim_date(date_key),
    meeting_status     VARCHAR(20) NOT NULL,
    no_show_flag       SMALLINT    NOT NULL,
    days_from_create   INTEGER,
    days_to_close      INTEGER
);
CREATE INDEX idx_fact_meetings_company ON fact_meetings(company_key);
CREATE INDEX idx_fact_meetings_rep     ON fact_meetings(rep_key);
CREATE INDEX idx_fact_meetings_date    ON fact_meetings(meeting_date_key);
CREATE INDEX idx_fact_meetings_deal    ON fact_meetings(deal_key);

CREATE TABLE fact_deals (
    deal_key          VARCHAR(10)  PRIMARY KEY,
    company_key       VARCHAR(10)  NOT NULL REFERENCES dim_company(company_key),
    rep_key           VARCHAR(6)   NOT NULL REFERENCES dim_rep(rep_key),
    source_key        VARCHAR(8)   NOT NULL REFERENCES dim_source(source_key),
    stage_key         VARCHAR(6)   NOT NULL REFERENCES dim_stage(stage_key),
    lost_reason_key   VARCHAR(6)   REFERENCES dim_lost_reason(lost_reason_key),
    created_date_key  INTEGER      NOT NULL REFERENCES dim_date(date_key),
    won_date_key      INTEGER      REFERENCES dim_date(date_key),
    lost_date_key     INTEGER      REFERENCES dim_date(date_key),
    mrr_usd           NUMERIC(12,2) NOT NULL DEFAULT 0,
    tcv_usd           NUMERIC(12,2) NOT NULL DEFAULT 0,
    deal_age_days     INTEGER,
    is_won            SMALLINT     NOT NULL,
    is_lost           SMALLINT     NOT NULL
);
CREATE INDEX idx_fact_deals_company ON fact_deals(company_key);
CREATE INDEX idx_fact_deals_rep     ON fact_deals(rep_key);
CREATE INDEX idx_fact_deals_source  ON fact_deals(source_key);
CREATE INDEX idx_fact_deals_stage   ON fact_deals(stage_key);
CREATE INDEX idx_fact_deals_created ON fact_deals(created_date_key);
CREATE INDEX idx_fact_deals_won     ON fact_deals(won_date_key);

-- ============================================================
-- LOAD HINT (Postgres)
-- After running this DDL, load the CSVs:
--   \copy dim_date         FROM 'data/dim_date.csv'         CSV HEADER;
--   \copy dim_company      FROM 'data/dim_company.csv'      CSV HEADER;
--   \copy dim_rep          FROM 'data/dim_rep.csv'          CSV HEADER;
--   \copy dim_campaign     FROM 'data/dim_campaign.csv'     CSV HEADER;
--   \copy dim_stage        FROM 'data/dim_stage.csv'        CSV HEADER;
--   \copy dim_lost_reason  FROM 'data/dim_lost_reason.csv'  CSV HEADER;
--   \copy dim_source       FROM 'data/dim_source.csv'       CSV HEADER;
--   \copy fact_calls       FROM 'data/fact_calls.csv'       CSV HEADER;
--   \copy fact_meetings    FROM 'data/fact_meetings.csv'    CSV HEADER;
--   \copy fact_deals       FROM 'data/fact_deals.csv'       CSV HEADER;
-- ============================================================

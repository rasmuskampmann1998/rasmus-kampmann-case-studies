-- Schema for the synthetic software-detection dataset.
-- Postgres flavour. Mirrors the public Danish CVR registry fields.

create schema if not exists software_detection;

create table software_detection.companies (
  cvr                  text primary key,        -- DK########
  company_name         text not null,
  company_form         text not null,           -- ApS / IVS / A_S / ENK / Holding
  industry_nace        text not null,           -- 5-digit code
  region               text not null,
  founded_year         smallint not null,
  employee_band        text not null,           -- 0 / 1-4 / 5-9 / 10-19 / 20-49 / 50+
  vat_frequency        text not null,           -- Monthly / Quarterly / Half-yearly
  has_subsidiaries     boolean not null,
  uses_target_software boolean not null
);

create index on software_detection.companies (company_form);
create index on software_detection.companies (industry_nace);
create index on software_detection.companies (employee_band);

-- Sample analytical query: positive-class rate by employee band
-- select employee_band,
--        count(*) as n,
--        round(avg(uses_target_software::int)::numeric, 3) as positive_rate
-- from software_detection.companies
-- group by employee_band
-- order by 1;

# Source scripts

The production ETL and refresh jobs live in the client's private repository.

The architecture mirrors what's in this folder:

- `etl/excel_to_supabase.py`. reads the four Excel files from SharePoint, validates
  schema, anonymises customer names, and upserts into the Supabase `european seed producer` schema.
- `etl/run_daily.yml`. GitHub Actions cron at 06:00 CET.
- `etl/run_weekly.yml`. GitHub Actions cron at 06:00 CET on Mondays (forecast/plan).
- `powerbi/Overview.pbix`. Power BI Desktop file connected to the Supabase warehouse.

For the public reproducible version, see [`../python/`](../python/).

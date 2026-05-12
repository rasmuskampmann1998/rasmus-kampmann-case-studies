# Source scripts

The production finance ETL lives in the client's private repository.

- `etl/accounting_to_supabase.py`. daily pull from the accounting system's CSV
  export endpoint, anonymises customer names, upserts into `european seed producer_fin`.
- `etl/payment_forecast.py`. fits a per-customer exponential-smoothing model on
  historical payment-lag behaviour and rolls a 14-day inflow forecast.
- `powerbi/Finance.pbix`. Power BI Desktop, connected to the Supabase warehouse.

For the public reproducible version, see [`../python/`](../python/).

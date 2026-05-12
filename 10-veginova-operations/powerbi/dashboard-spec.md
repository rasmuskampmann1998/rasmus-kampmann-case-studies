# A European seed producer Operations. Power BI Dashboard Spec

## Pages

### 1. Sales Pulse
**Question:** How is the order book tracking vs. plan?

- KPI cards: YTD revenue, YTD volume, # active customers, top-customer concentration (top-5 share)
- Line chart: monthly orders vs. same period last year
- Stacked bar: orders by region × channel
- Top-10 customers (anonymised) table with order count + total volume
- Slicers: date range, region, seed family

### 2. Inventory Cover
**Question:** Which seeds are over/understocked vs. forecasted sell-through?

- Big number: # seeds in RED band (< 2 months cover)
- Donut: RED / AMBER / GREEN cover-band distribution
- Detail table: seed_code, on_hand_kg, monthly_sales_kg, months_of_cover, band
- Conditional formatting on `months_of_cover` (red < 2, amber 2–6, green > 6)
- Slicers: seed family, location

### 3. Production Schedule
**Question:** Which production runs are at risk of missing their delivery window?

- Big number: # mismatch flags (production finishes after delivery opens)
- Gantt-style timeline: planned production windows vs. contracted delivery windows per seed
- Red dot annotation on every flagged seed
- Detail table: seed_code, production_finish, next_delivery_open, days_late
- Slicers: status (planned / in_progress), scenario

### 4. 24-Month Forecast
**Question:** What does the rolling 24-month volume forecast look like, and how has it shifted?

- Stacked area: base / upside / downside scenarios over 24 months
- Line chart: this quarter's forecast vs. last quarter's (delta highlight)
- Pareto chart: top-15 seeds by forecast volume
- KPI: forecast MAPE (last 6 months). currently ~22%
- Slicers: scenario, seed family

## DAX Measures

```dax
-- Sales
Total Volume YTD =
    CALCULATE (
        SUM ( sales_orders[qty] ),
        DATESYTD ( 'Date'[Date] )
    )

Total Volume LY YTD =
    CALCULATE (
        SUM ( sales_orders[qty] ),
        SAMEPERIODLASTYEAR ( DATESYTD ( 'Date'[Date] ) )
    )

Top-5 Customer Concentration % =
    VAR Top5Total =
        SUMX (
            TOPN ( 5, VALUES ( sales_orders[customer_id] ), [Total Volume YTD] ),
            [Total Volume YTD]
        )
    RETURN DIVIDE ( Top5Total, [Total Volume YTD] )

-- Inventory cover
Avg Monthly Sales 90d =
    CALCULATE (
        SUM ( sales_orders[qty] ) / 3,
        DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -90, DAY )
    )

Stock On Hand =
    CALCULATE (
        SUM ( inventory_log[qty_on_hand] ),
        FILTER (
            ALL ( inventory_log ),
            inventory_log[last_count_date] >= MAX ( inventory_log[last_count_date] ) - 14
        )
    )

Months Of Cover =
    DIVIDE ( [Stock On Hand], [Avg Monthly Sales 90d] )

Cover Band =
    SWITCH (
        TRUE (),
        [Months Of Cover] < 2,  "RED",
        [Months Of Cover] < 6,  "AMBER",
        "GREEN"
    )

-- Production
Mismatch Days =
    VAR ProdFinish = MIN ( production_plan[finish_date] )
    VAR DeliveryOpen = MIN ( sales_orders[delivery_window_from] )
    RETURN IF ( ProdFinish > DeliveryOpen, DATEDIFF ( DeliveryOpen, ProdFinish, DAY ), BLANK () )

-- Forecast MAPE
Forecast MAPE % =
    AVERAGEX (
        VALUES ( forecast_24m[period_yyyymm] ),
        DIVIDE (
            ABS ( [Total Volume YTD] - SUM ( forecast_24m[forecast_qty] ) ),
            [Total Volume YTD]
        )
    )
```

## Refresh schedule

- **Sales + inventory:** daily 06:00 CET via GitHub Actions ETL → Supabase
- **Production + forecast:** weekly Monday 06:00 CET
- **Power BI dataset refresh:** twice daily (07:00 + 14:00 CET) via Power BI Service scheduled refresh

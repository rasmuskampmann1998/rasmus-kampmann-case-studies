# A European seed producer Invoices & Finance. Power BI Dashboard Spec

## Pages

### 1. AR Ageing
**Question:** What's overdue, and which customers are driving it?

- KPI cards: total overdue €, # overdue invoices, DSO (days), week-over-week delta
- Stacked bar: outstanding € by ageing bucket (0–30 / 31–60 / 61–90 / 90+)
- Top-10 overdue customers table with drill-through to invoice detail
- Slicers: customer, ageing bucket, date range

### 2. Cash Collection Forecast
**Question:** How much cash should land in the next 14 days, and from whom?

- KPI: forecast cash-in next 14 days, with ±9% confidence band
- Stacked column: daily projected inflows by customer
- Variance line: this week's forecast vs. last week's
- Detail table: customer, expected_amount, expected_date, confidence

### 3. Gross Margin by Seed
**Question:** Which seeds are profitable, and which are running thin?

- Horizontal bar: gross margin % per seed, sorted ascending, colour-coded (<15% red)
- KPI: # seeds below 15% margin floor
- Scatter: kg sold (x) vs. margin % (y). quadrant analysis
- Slicers: seed family, customer

### 4. Customer Profitability
**Question:** Which customers contribute most to gross profit, not just revenue?

- Scatter: revenue (x) vs. gross profit (y), one dot per customer, sized by # invoices
- Side-by-side rank table: top 10 by revenue | top 10 by gross profit (with rank delta)
- Drill-through to customer detail page (12-month order history, payment behaviour, margin breakdown by seed)

## DAX Measures

```dax
-- AR ageing
Outstanding EUR =
    SUMX (
        invoice_status,
        invoice_status[amount_eur] - invoice_status[paid_eur]
    )

Total Overdue EUR =
    CALCULATE (
        [Outstanding EUR],
        invoice_status[derived_status] = "overdue"
    )

DSO Days =
    AVERAGEX (
        FILTER (
            invoice_status,
            invoice_status[derived_status] = "paid"
        ),
        DATEDIFF ( invoice_status[issue_date], invoice_status[payment_date], DAY )
    )

-- Margin
Revenue EUR = SUM ( invoices[amount_eur] )

Cost EUR =
    SUMX (
        sales_orders,
        sales_orders[qty]
            * RELATED ( production_cost[cost_per_kg_eur] )
    )

Gross Margin % =
    DIVIDE ( [Revenue EUR] - [Cost EUR], [Revenue EUR] )

Seeds Below Floor =
    COUNTROWS (
        FILTER (
            VALUES ( sales_orders[seed_code] ),
            [Gross Margin %] < 0.15
        )
    )

-- Customer profitability
Customer Revenue Rank =
    RANKX ( ALL ( invoices[customer_id] ), [Revenue EUR],, DESC )

Customer GP Rank =
    RANKX ( ALL ( invoices[customer_id] ), [Revenue EUR] - [Cost EUR],, DESC )

Rank Delta = [Customer Revenue Rank] - [Customer GP Rank]
```

## Refresh schedule

- **Invoices + payments:** twice daily (07:00 + 14:00 CET) via Python ETL
- **Production cost:** weekly Monday 06:00 CET
- **Power BI dataset:** auto-refresh tied to ETL completion

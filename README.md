# Rasmus Kampmann: Case Studies

Four production data, BI, and AI projects across operations, finance, ML, and market intelligence. Each one is a reproducible analytics extract with anonymised or synthetic data, SQL, Python, Power BI specs, and slide-deck blueprints.

The portfolio site at [rasmuskampmann.com](https://rasmuskampmann.com) walks through each case study for non-technical readers. This repo is the technical companion.

## Case studies

| # | Case study | Domain | Key skill |
|---|---|---|---|
| 03 | [Software Detection ML Model](03-software-detection-ml/) | Sales intelligence | XGBoost classifier on CVR-only synthetic data, AUC 0.74-0.78 |
| 07 | [Market Intelligence Platform (Tomato Intel)](07-tomato-intel/) | Market intelligence | Agentic scraping, RAG, semantic search, SQL migrations, live demo |
| 10 | [Operations & 24-Month Forecasting](10-veginova-operations/) | Operations | SQL warehouse, ETL, Power BI, 24-month rolling forecast |
| 11 | [Invoice & Financial Dashboard](11-veginova-invoices/) | Finance | AR ageing, gross margin per SKU, cash collection forecast |

Cases 10 and 11 are anonymised real engagements (a European seed producer). Case 03 uses a fully synthetic dataset of fictive Danish companies. Case 07 is built around an agricultural-technology client with a live public demo at [tomato-intel-api.onrender.com](https://tomato-intel-api.onrender.com).

## Folder convention

Each case study contains some or all of:

- `README.md` non-technical narrative plus key findings
- `data/` anonymised or synthetic CSV samples
- `sql/` schema and analytical queries (Postgres flavour)
- `python/` reproducible analysis scripts (typically 5-7 charts)
- `powerbi/` dashboard spec plus DAX measures
- `slides/` McKinsey one-rule executive deck spec
- `source-scripts/` architecture notes pointing to production code

Case 07 (Tomato Intel) only includes `python/`, `powerbi/`, `slides/`, and `source-scripts/` because the production scrapers can't be reproduced publicly. Cases 03, 10, 11 have the full set.

## Reproducing locally

```bash
git clone https://github.com/rasmuskampmann1998/rasmus-kampmann-case-studies.git
cd rasmus-kampmann-case-studies
pip install -r requirements.txt
cd <case-study-folder>/python
python analysis.py
```

Some case studies generate their own dataset deterministically (`generate_synthetic_data.py` or `generate_sample_data.py`) so the CSV inputs reproduce identically across runs.

## Anonymisation

Cases 10 and 11 anonymise all customer names, company identifiers, seed codes, and absolute amounts. Volumes are scaled by random factors per row to avoid revealing commercial data, while preserving the structural patterns the case studies describe. Case 03 uses entirely fictive data with no relation to any real company.

## Contact

- Portfolio: [rasmuskampmann.com](https://rasmuskampmann.com)
- LinkedIn: [linkedin.com/in/rasmuskampmann](https://www.linkedin.com/in/rasmuskampmann/)
- Email: rasmuskampmann1998@gmail.com

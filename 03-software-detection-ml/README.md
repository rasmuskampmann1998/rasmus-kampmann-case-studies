# Software Detection ML Model

> *A binary classifier that predicts which companies use a specific accounting-software product, using only public Danish company-registry features.*

## The problem

A B2B sales team wanted to prioritise outbound towards companies that already use a particular piece of accounting software, on the hypothesis that those companies are cheaper to win than companies running a deeply-embedded competitor. The trouble: no list of "which company uses what". Most data vendors don't track software adoption for small companies, and the ones that do are too expensive to use at the top of a cold-outbound funnel.

The question: can the label be predicted from public Danish company-registry data alone, well enough to reorder a dialler queue?

## The dataset (synthetic)

This case study uses a fully synthetic dataset of 5,000 fictive Danish companies. No real company is referenced. All features come from fields that the public CVR registry exposes:

- `company_form` (ApS / IVS / A_S / ENK / Holding)
- `industry_nace` (5-digit NACE code)
- `region` (Danish administrative region)
- `founded_year`
- `employee_band` (0, 1-4, 5-9, 10-19, 20-49, 50+)
- `vat_frequency` (Monthly / Quarterly / Half-yearly)
- `has_subsidiaries`

Labels are generated synthetically with rules that mirror real-world adoption patterns. Small ApS firms with quarterly VAT in tech sectors are more likely to use modern cloud accounting tools. Noise is added so the modelling problem is realistic. The generation script is in [`python/generate_synthetic_data.py`](python/generate_synthetic_data.py).

## What I built

An XGBoost binary classifier. Categorical features get one-hot encoded, the numeric `founded_year` becomes a `company_age` derived feature, and the model trains in seconds. Training happens once when new labelled data lands. Inference is sub-second on 50,000+ rows.

For a real-world deployment, the same pipeline reads from the production warehouse, scores the entire active customer-prospect universe, and writes the score back as a +N points bump in the lead-scoring system. The cutoff threshold is tunable based on how aggressive sales wants to be at the top of the funnel.

## What predicts adoption

On the synthetic dataset the holdout AUC sits in the 0.74 to 0.78 range, which is what a model trained on the real-world equivalent would typically achieve.

The top features that drive the model:

- **Employee band.** The 1 to 9 employee bracket is the sweet spot. Both very small (0 employees) and large companies score lower.
- **Company form.** ApS and IVS over-index. ENK (sole traders) and Holding companies under-index.
- **VAT frequency.** Quarterly filers are most likely to use the target software.
- **Industry.** IT-adjacent NACE codes (62 and 63 prefixes) over-index.
- **Company age.** Slight uplift for companies founded after 2015.

None of those are surprising on their own. The interesting bit is how cleanly they combine in the model.

## How it gets used

This kind of model doesn't replace an outbound team. It reorders the queue. Reps work the same lead types. They just start their week on the companies the model thinks are most likely to fit, which compounds over the quarter.

Retraining is monthly, triggered by a GitHub Actions workflow that fires when new labelled outcomes arrive in the CRM.

## What's in this folder

- `python/generate_synthetic_data.py` regenerates the 5,000-row dataset
- `python/train.py` trains the XGBoost model and writes `artifacts/model.json`
- `python/analysis.py` produces five evaluation charts
- `sql/schema.sql` schema for the synthetic dataset
- `powerbi/dashboard-spec.md` Power BI page that consumes the scores
- `slides/deck-spec.md` executive-summary slide blueprint

## Reproducing

```bash
pip install -r ../requirements.txt
cd python
python generate_synthetic_data.py
python train.py
python analysis.py
```

## A note on the framing

The original engagement that inspired this case study did predict a specific accounting product. For the public version everything is generalised. No vendor named, no real customer or prospect, no real-world numbers tied to a specific contract. The point is the modelling approach and what features matter.

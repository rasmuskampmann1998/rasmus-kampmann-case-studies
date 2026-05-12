# Slide Deck Spec: Software Detection Model

McKinsey one-rule format. One problem, one finding (action title), one recommendation per slide.

## Slide 1: Cover

**Title:** Predicting accounting-software adoption from public registry data alone
**Subtitle:** A classifier built on CVR-only features identifies high-probability users, no enrichment vendor required.

## Slide 2: Executive summary (SCR)

- **Situation:** Users of the target software product are a high-value ICP segment, but identifying them across the full SMB universe currently requires manual checking or paid enrichment data.
- **Complication:** Manual checking doesn't scale; paid enrichment is too expensive to apply at the top of a cold-outbound funnel.
- **Resolution:** A gradient-boosted binary classifier trained on public CVR registry features achieves holdout AUC in the 0.74 to 0.78 range. Good enough to score the full universe and prioritise sales attention.

## Slide 3: Finding 1

**Action title:** *Public CVR data alone predicts software adoption well above chance.*
- Chart: ROC curve on holdout, with diagonal random baseline.
- Therefore: Deploy the model to score the universe before the next outbound campaign.

## Slide 4: Finding 2

**Action title:** *The top-scoring 10% of companies convert at multiples of the base rate.*
- Chart: cumulative lift vs percentile rank.
- Therefore: Use the top two score deciles as the priority list. Deprioritise the bottom 60%.

## Slide 5: Finding 3

**Action title:** *Employee band and company form drive most of the signal.*
- Chart: feature importance, top-15.
- Therefore: The model captures patterns a senior salesperson already intuits. The value is consistency at scale, not novel discovery.

## Slide 6: Finding 4

**Action title:** *Plugging the score into lead-scoring shifts the dial list's average score before a single call is made.*
- Chart: before-and-after histogram of lead scores with and without the model boost.
- Therefore: Integrate the score permanently into the lead-scoring pipeline as a feature.

## Slide 7: Next steps

1. Score the full active universe on a daily cron.
2. Integrate into the scoring pipeline as a numerical feature.
3. Re-train monthly as new labelled outcomes arrive in the CRM.
4. Monitor model drift; alert on AUC degradation week over week.

## Slide 8: A note on the public version

The original engagement predicted a specific vendor's product on real CVR data. This public version uses a synthetic dataset of 5,000 fictive companies and generic feature framing. The modelling approach, evaluation, and integration pattern transfer cleanly to any equivalent problem.

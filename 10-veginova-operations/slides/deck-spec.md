# Operations Dashboard: Executive Deck Spec

McKinsey one-rule format. One problem, one finding (action title), one recommendation per slide.

## Slide 1: Cover

**Title:** A live system that tells the business what to produce, how much, and when.
**Subtitle:** The planner's red/green sheet, made live, and validated against their own numbers.

## Slide 2: Executive summary (SCR)

- **Situation:** Production planning ran on a spreadsheet maintained by hand, stale the moment a sale landed or stock changed.
- **Complication:** Seed takes about a year to produce, so a stockout is discovered twelve months too late to fix. The plan had to be both current and forward-looking.
- **Resolution:** A live planning system. The engine is one SQL view; Power BI renders it. It reproduces the planner's own numbers exactly and updates itself as sales and stock change.

## Slide 3: Finding 1

**Action title:** *The engine reproduces the planner's spreadsheet exactly, zero mismatches against the anchor varieties.*
- Chart: the validation gate (anchor varieties, computed vs. expected).
- Therefore: the system can be trusted to run the plan, because it agrees with the sheet the planner already trusts.

## Slide 4: Finding 2

**Action title:** *A variety can be red yet need zero production, so the warning light and the production order are two different things.*
- Chart: red/green status beside production need.
- Therefore: show both. A red flag means "watch," not "make more," unless production need is also above zero.

## Slide 5: Finding 3

**Action title:** *The one-year lead time means a shortage has to be seen early or it can't be fixed at all.*
- Chart: ending stock by variety against the safety line.
- Therefore: the plan flags not just which varieties are short, but when production has to start to cover them in time.

## Slide 6: Scenario testing

**Action title:** *The planner can pressure-test a big sale, a capacity drop, or a stock loss before committing seed to a year in the ground.*
- Chart: what-if slider moving production need live.
- Therefore: decisions are tested against scenarios before they're made, not discovered after.

## Slide 7: What this is, honestly

**Action title:** *This is a planning system with scenario testing, not a statistical forecast.*
- The business runs on named deals, not predictable trends. The planner's judgment is the input; the system makes it live, fast, and forward-looking.
- Therefore: the win is reproducing the planner's numbers and keeping them current, not predicting demand the data can't support.

## Slide 8: Next steps

- Seed the production buffer (floor + months-of-cover per variety) so "produce" becomes a final number, not "just enough not to go negative."
- Add the write layer so the planner commits plans from the app, building the plan-vs-actual history the snapshot mechanism already supports.
- Validate the multi-year view once a second sales year is seeded.

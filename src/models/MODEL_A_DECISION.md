# Model A: Model Selection Decision

**Task:** Predict project outcome (TERMINATED=failure vs CLOSED=success)
from proposal text + structured features. Imbalanced (~93/7).

## Candidates compared

| Model | Features | ROC-AUC | PR-AUC |
|-------|----------|---------|--------|
| LogReg + TF-IDF (baseline) | text + structured | **0.913** | **0.369** |
| DistilBERT + LoRA | text only | 0.772 | 0.166 |

(PR-AUC random floor = 0.066)

## Decision: ship the baseline.

The logistic-regression baseline beats the fine-tuned transformer on both
metrics. The transformer saw only the objective text; the baseline also used
the structured features (funding scheme, EC contribution, consortium size),
which carry most of the outcome signal (small single-beneficiary grants fail
far more than large consortia). The text alone is weakly predictive of outcome.

We shipped the simpler, faster, more accurate model. The transformer
experiment is retained as the evidence justifying that choice.

## Leakage check
`durationMonths` ablated with zero metric change, confirming the baseline's
score is not from outcome-encoding features.
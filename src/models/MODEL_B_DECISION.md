# Model B: Budget Anomaly Detector

**Task:** Flag whether a project's EC contribution is anomalous FOR ITS
FUNDING SCHEME. Conditioning on scheme is essential (Phase 1: two budget
regimes, ~187k solo grants vs ~5M consortia; a global detector is meaningless).

## Method: per-scheme robust z-score (median / MAD)

- Compute median and MAD of log10(budget) within each funding scheme
  (schemes with >= 30 funded projects).
- Flag budgets beyond |z| > 3.5 robust deviations.
- **MAD floor (0.05 in log10 space, ~12% in EUR):** many schemes are
  budget-capped (e.g. ERC-STG mostly at 1.5M), giving near-zero spread that
  explodes z-scores. The floor treats budgets within ~12% of the scheme norm
  as normal. Without it, ~10% of projects were falsely flagged with
  impossible z-scores (e.g. -631). With it: 1.57% flagged, sane z-scores.

## Result
- 34,948 projects scored across 32 schemes.
- 548 flagged (1.57%), a healthy anomaly rate.
- Anomalies are genuine (e.g. a 255k MSCA-ITN where the norm is ~3.8M).

## Honest framing
UNSUPERVISED: CORDIS has no anomaly label. "Anomaly" here means "unusual
among funded projects for this scheme", NOT "fraudulent" or "wrong". The
Budget agent presents flags as questions to review, not verdicts.

## Agent interface
`score_budget(scheme, ec_contribution)` returns a verdict plus a plain-English
explanation the agent uses to justify the flag. The "model" is a small JSON
of per-scheme median+spread, fully interpretable, no black box.

## Why not Isolation Forest (yet)
The z-score method is more interpretable, which the agent needs to explain
flags. An Isolation Forest on multiple features (budget, cost-per-partner,
duration) is a possible extension but adds opacity for marginal gain here.
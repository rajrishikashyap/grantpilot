"""
Phase 2: Model B - budget anomaly detector.

Flags projects whose EC contribution is anomalous FOR THEIR FUNDING SCHEME.
Conditioning on scheme is essential (Phase 1 finding: two budget regimes,
~187k solo grants vs ~5M consortia; a global detector is meaningless).

UNSUPERVISED: CORDIS has no 'anomaly' label. We define anomaly statistically
as strong deviation from the funded norm within a scheme. This means
'unusual among funded projects', NOT 'fraudulent'. Documented honestly.

Approach 1 (this file): per-scheme robust z-score (median / MAD).
Interpretable and explainable, which the Budget agent needs to justify flags.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd

CLEAN = Path("data/clean")
MODELS = Path("models")
MODELS.mkdir(exist_ok=True)

# Robust z uses median + MAD (median absolute deviation), resistant to the
# very outliers we are hunting, unlike mean + std which they distort.
MAD_TO_STD = 1.4826  # scale factor so MAD approximates std for normal data
Z_THRESHOLD = 3.5    # flag beyond ~3.5 robust std devs (a common cutoff)
MIN_GROUP = 30       # schemes with fewer projects: not enough to judge normalcy
MAD_FLOOR = 0.05     # min spread in log10 space (~12% in EUR). Prevents z-score
                     # explosion when a scheme has a capped/near-constant budget.


def build():
    df = pd.read_parquet(CLEAN / "projects_clean.parquet")
    # We work on log budget (Phase 1: log-normal). Guard against zero/neg.
    df = df[df["ecMaxContribution"] > 0].copy()
    df["logBudget"] = np.log10(df["ecMaxContribution"])

    print(f"Projects with valid budget: {len(df):,}")
    print(f"Funding schemes: {df['fundingScheme'].nunique()}")

    # Per-scheme median and MAD of log budget
    stats = {}
    df["robustZ"] = np.nan

    for scheme, grp in df.groupby("fundingScheme"):
        if len(grp) < MIN_GROUP:
            continue  # too small to define 'normal' reliably
        med = grp["logBudget"].median()
        mad = (grp["logBudget"] - med).abs().median() * MAD_TO_STD
        # Floor the spread: capped schemes (e.g. ERC-STG mostly at 1.5M) have
        # near-zero MAD, which would explode z-scores. The floor treats budgets
        # within ~12% of the scheme norm as normal, not anomalous.
        mad = max(mad, MAD_FLOOR)
        z = (grp["logBudget"] - med) / mad
        df.loc[grp.index, "robustZ"] = z
        stats[scheme] = {
            "median_log": round(float(med), 4),
            "mad_log": round(float(mad), 4),
            "n": int(len(grp)),
            "median_eur": round(float(10**med)),
        }

    # Flag anomalies
    df["isAnomaly"] = df["robustZ"].abs() > Z_THRESHOLD
    n_flagged = df["isAnomaly"].sum()
    n_scored = df["robustZ"].notna().sum()

    print(f"\nScored (in schemes with >= {MIN_GROUP} projects): {n_scored:,}")
    print(f"Flagged as anomalous (|z| > {Z_THRESHOLD}): {n_flagged:,} "
          f"({n_flagged/n_scored*100:.2f}%)")

    # Show a few examples of what got flagged
    print("\nExample anomalies (largest |z|):")
    top = df[df["isAnomaly"]].reindex(
        df[df["isAnomaly"]]["robustZ"].abs().sort_values(ascending=False).index
    ).head(8)
    for _, r in top.iterrows():
        print(f"  {r['fundingScheme']:15s} {r['ecMaxContribution']:>14,.0f} EUR  "
              f"z={r['robustZ']:+.1f}  ({r['acronym']})")

    # Save the per-scheme stats, this IS the model (the Budget agent uses it)
    (MODELS / "model_b_scheme_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\nSaved per-scheme stats to models/model_b_scheme_stats.json "
          f"({len(stats)} schemes)")


def score_budget(scheme: str, ec_contribution: float,
                 stats_path=MODELS / "model_b_scheme_stats.json") -> dict:
    """Score ONE budget for the Budget agent. Returns a verdict + explanation.
    This is what the agent calls at inference time."""
    stats = json.loads(Path(stats_path).read_text())

    if scheme not in stats:
        return {"scored": False,
                "reason": f"No budget norm available for scheme '{scheme}' "
                          f"(too few funded examples)."}
    if ec_contribution <= 0:
        return {"scored": False, "reason": "Budget must be positive."}

    s = stats[scheme]
    log_b = np.log10(ec_contribution)
    z = (log_b - s["median_log"]) / max(s["mad_log"], MAD_FLOOR)
    is_anom = abs(z) > Z_THRESHOLD
    direction = "far above" if z > 0 else "far below"

    return {
        "scored": True,
        "scheme": scheme,
        "budget_eur": ec_contribution,
        "scheme_median_eur": s["median_eur"],
        "robust_z": round(float(z), 2),
        "is_anomaly": bool(is_anom),
        "explanation": (
            f"{ec_contribution:,.0f} EUR is {direction} the typical "
            f"{scheme} grant (median {s['median_eur']:,.0f} EUR), z={z:+.1f}."
            if is_anom else
            f"{ec_contribution:,.0f} EUR is within the normal range for "
            f"{scheme} (median {s['median_eur']:,.0f} EUR, z={z:+.1f})."
        ),
    }


if __name__ == "__main__":
    build()
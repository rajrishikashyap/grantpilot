"""
Precompute analytics over the full CORDIS dataset for the dashboard.

The frontend dashboard should not recompute aggregates over 35k rows on every
page load, and the API should not touch the dataframe per request. So we compute
five aggregates once here and write them to models/grant_stats.json, which the
API serves as a static blob via GET /stats.

Run from the repo root:
    python -m src.data.compute_stats

Reads data/clean/projects_clean.parquet (the canonical cleaned table produced by
src/data/clean.py). If a column name differs in your build, the error will name
it and you can adjust the COLS below.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

CLEAN = Path("data/clean/projects_clean.parquet")
OUT = Path("models/grant_stats.json")

# Column names in the cleaned table. Adjust here if your build differs.
COL_SCHEME = "fundingScheme"
COL_STATUS = "status"
COL_MONEY = "ecMaxContribution"  # raw EUR float (the pipeline log-transforms it)

MIN_N = 100  # ignore schemes with too few projects in per-scheme breakdowns
TOP = 12     # cap bars so the charts stay legible


def main():
    if not CLEAN.exists():
        raise SystemExit(
            f"{CLEAN} not found. It is produced by src/data/clean.py. "
            "Run the cleaning step first, or point CLEAN at your parquet."
        )

    df = pd.read_parquet(CLEAN)
    for col in (COL_SCHEME, COL_STATUS, COL_MONEY):
        if col not in df.columns:
            raise SystemExit(
                f"Column '{col}' not in {CLEAN}. Columns present: {list(df.columns)}"
            )

    total = int(len(df))

    # 1. Projects by scheme (top schemes by count).
    by_scheme = (
        df[COL_SCHEME].value_counts().head(TOP)
        .rename_axis("scheme").reset_index(name="count")
        .to_dict("records")
    )

    # 2. Status split (whole corpus).
    status = {str(k): int(v) for k, v in df[COL_STATUS].value_counts().items()}

    # 3. Failure rate by scheme: TERMINATED / (CLOSED + TERMINATED).
    # Only decided projects count; a scheme needs MIN_N decided projects.
    decided = df[df[COL_STATUS].isin(["CLOSED", "TERMINATED"])]
    failure = []
    for scheme, g in decided.groupby(COL_SCHEME):
        n = len(g)
        if n < MIN_N:
            continue
        rate = float((g[COL_STATUS] == "TERMINATED").mean())
        failure.append({"scheme": str(scheme), "rate": round(rate, 4), "n": int(n)})
    failure.sort(key=lambda r: r["rate"], reverse=True)
    failure_rate_by_scheme = failure[:TOP]

    # 4. Median EC contribution by scheme (EUR).
    ec = pd.to_numeric(df[COL_MONEY], errors="coerce")
    money = df.assign(_ec=ec).dropna(subset=["_ec"])
    medians = []
    for scheme, g in money.groupby(COL_SCHEME):
        if len(g) < MIN_N:
            continue
        medians.append({
            "scheme": str(scheme),
            "median_eur": int(g["_ec"].median()),
            "n": int(len(g)),
        })
    medians.sort(key=lambda r: r["median_eur"], reverse=True)
    median_budget_by_scheme = medians[:TOP]

    # 5. Budget distribution: histogram of log10(EUR), 20 bins.
    pos = money["_ec"][money["_ec"] > 0]
    counts, edges = np.histogram(np.log10(pos), bins=20)
    budget_histogram = {
        "bin_edges_log10": [round(float(e), 3) for e in edges],
        "counts": [int(c) for c in counts],
    }

    stats = {
        "total": total,
        "by_scheme": by_scheme,
        "status": status,
        "failure_rate_by_scheme": failure_rate_by_scheme,
        "median_budget_by_scheme": median_budget_by_scheme,
        "budget_histogram": budget_histogram,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2))

    print(f"Wrote {OUT} from {total} projects.")
    print(f"  schemes charted:        {len(by_scheme)}")
    print(f"  status buckets:         {status}")
    print(f"  failure rates (top 3):  {failure_rate_by_scheme[:3]}")
    print(f"  median budgets (top 3): {median_budget_by_scheme[:3]}")
    print("Sanity check: median_eur values should look like real EUR (millions).")


if __name__ == "__main__":
    main()
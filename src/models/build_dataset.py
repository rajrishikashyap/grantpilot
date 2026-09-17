"""
Phase 2: build the Model A labeled dataset.

Task: predict project OUTCOME (CLOSED=success vs TERMINATED=failure)
from proposal text + structured features.

- Keep only CLOSED and TERMINATED (SIGNED excluded: outcome unknown).
- Label: 1 = TERMINATED (failure, the minority/positive-of-interest class),
         0 = CLOSED (success).
  We make FAILURE the positive class (1) because that is what we want the
  model to detect, the rare, costly event. This matters for precision/recall.
- Stratified split so the 93/7 ratio is preserved in train and test.
"""

from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

CLEAN = Path("data/clean")
OUT = Path("data/clean")

# Structured features we engineered in Phase 1 (all leak-free: known at
# proposal time, except we must be careful, see note below).
STRUCTURED = [
    "ecMaxContribution",
    "totalCost",
    "durationMonths",
    "consortiumSize",
    "numCountries",
    "numSME",
    "numHES",
    "numREC",
    "numPRC",
    "numPUB",
    "fundingScheme",   # categorical, encoded later
]

TEXT = "objective"
LABEL_SRC = "status"


def build():
    df = pd.read_parquet(CLEAN / "projects_clean.parquet")
    print(f"Loaded {len(df):,} projects")

    # Keep only decided outcomes
    df = df[df[LABEL_SRC].isin(["CLOSED", "TERMINATED"])].copy()
    print(f"After keeping CLOSED/TERMINATED: {len(df):,}")

    # Label: failure = 1
    df["label"] = (df[LABEL_SRC] == "TERMINATED").astype(int)
    print(f"Label balance: {df['label'].mean()*100:.1f}% failures (positive class)")

    # Keep only the columns we need
    keep = STRUCTURED + [TEXT, "label", "id"]
    df = df[keep].dropna(subset=[TEXT])  # objective must exist
    print(f"After dropping missing objective: {len(df):,}")

    # Stratified split, preserve imbalance in both halves
    train, test = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["label"]
    )
    print(f"\nTrain: {len(train):,}  ({train['label'].mean()*100:.1f}% failures)")
    print(f"Test:  {len(test):,}  ({test['label'].mean()*100:.1f}% failures)")

    train.to_parquet(OUT / "model_a_train.parquet", index=False)
    test.to_parquet(OUT / "model_a_test.parquet", index=False)
    print(f"\nWrote model_a_train.parquet and model_a_test.parquet")


if __name__ == "__main__":
    build()
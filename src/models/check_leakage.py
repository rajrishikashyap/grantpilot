"""Check whether duration/cost leak the outcome (are they suspiciously
different for TERMINATED vs CLOSED?). If duration is far shorter for
failures, it may encode the termination itself, that would be leakage."""
import pandas as pd
from pathlib import Path

tr = pd.read_parquet(Path("data/clean/model_a_train.parquet"))

for col in ["durationMonths", "totalCost", "ecMaxContribution", "consortiumSize"]:
    print(f"\n{col}:")
    print(tr.groupby("label")[col].median().rename({0: "CLOSED", 1: "TERMINATED"}))
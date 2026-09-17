"""Confirm every project got consortium features, no silent NaN from the join."""
import pandas as pd
from pathlib import Path

df = pd.read_parquet(Path("data/clean/projects_clean.parquet"))
print(f"Clean table rows: {len(df):,}")

# How many projects have NO consortium size (join miss)?
missing = df["consortiumSize"].isna().sum()
print(f"Projects missing consortiumSize (join miss): {missing:,}")

# Spot-check a few key engineered columns for completeness
for col in ["consortiumSize", "numCountries", "hasCoordinator",
            "ecMaxContribution", "durationMonths", "topicCode", "legalBasisCode"]:
    n_missing = df[col].isna().sum()
    print(f"  {col:20s} missing: {n_missing:,} ({n_missing/len(df)*100:.1f}%)")
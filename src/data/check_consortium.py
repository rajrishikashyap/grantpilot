"""Diagnose the consortium-size result: is median=1 real or a join bug?"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from load import load_organizations

orgs = load_organizations()
print(f"Total org rows: {len(orgs):,}")
print(f"Distinct projectIDs in orgs: {orgs['projectID'].nunique():,}")

sizes = orgs.groupby("projectID").size()
print("\nConsortium size distribution (orgs per project):")
print(sizes.describe())
print("\nSize value counts (top 10):")
print(sizes.value_counts().sort_index().head(10))

# Cross-check: how many projects have exactly 1 org?
print(f"\nProjects with exactly 1 org: {(sizes == 1).sum():,} "
      f"({(sizes == 1).mean()*100:.1f}%)")

# Sanity: check the 'role' column values, coordinator detection depends on it
print("\nRole value counts:")
print(orgs['role'].value_counts())
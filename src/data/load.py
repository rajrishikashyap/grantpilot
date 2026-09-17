"""
GrantPilot data loaders for raw CORDIS H2020 CSVs.

Every raw file is semicolon-separated, double-quoted, UTF-8.
These loaders read them safely and return pandas DataFrames.
We keep loading and cleaning separate: this module only READS.
"""

from pathlib import Path
import pandas as pd

RAW = Path("data/raw")

# CORDIS uses ';' as separator and '"' as quote char. UTF-8 with occasional
# odd bytes, so we read as str first and coerce types later in clean.py.
_READ_OPTS = dict(
    sep=";",
    quotechar='"',
    encoding="utf-8",
    encoding_errors="replace",
    dtype=str,          # read everything as text first; we cast deliberately later
    keep_default_na=False,  # keep empty strings as "", do not guess NaN yet
    on_bad_lines="warn",    # tell us if any row fails to parse, do not crash
)


def load_projects() -> pd.DataFrame:
    """The spine: one row per project (22 columns)."""
    return pd.read_csv(RAW / "project.csv", **_READ_OPTS)


def load_organizations() -> pd.DataFrame:
    """One row per (organization x project). Joins to projects on projectID."""
    return pd.read_csv(RAW / "organization.csv", **_READ_OPTS)


def load_topics() -> pd.DataFrame:
    """Call topic per project. Joins on projectID."""
    return pd.read_csv(RAW / "topics.csv", **_READ_OPTS)


def load_legal_basis() -> pd.DataFrame:
    """Legal basis / programme part per project. Joins on projectID."""
    return pd.read_csv(RAW / "legalBasis.csv", **_READ_OPTS)


if __name__ == "__main__":
    # Quick sanity check: load each, print shape and confirm the key columns.
    for name, loader in [
        ("projects", load_projects),
        ("organizations", load_organizations),
        ("topics", load_topics),
        ("legalBasis", load_legal_basis),
    ]:
        df = loader()
        print(f"{name:15s} shape={df.shape}  columns={list(df.columns)[:4]}...")
    print("\nProjects: key columns present?")
    p = load_projects()
    for col in ["id", "objective", "ecMaxContribution", "fundingScheme", "status"]:
        print(f"  {col:20s} -> {'OK' if col in p.columns else 'MISSING'}")
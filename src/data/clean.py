"""
GrantPilot cleaning pipeline for CORDIS H2020.

Turns the raw linked tables into ONE clean per-project table.
Run stages in order; each is a plain function so you can test in isolation.

Design choices (documented on purpose, this is the data-honesty layer):
- Money fields: CORDIS may use European decimals. We strip thousands sep,
  swap decimal comma to dot, then coerce. Bad values become NaN, not crashes.
- Org rows are collapsed per project into consortium features.
- Empty objective text is KEPT but flagged, we decide drop policy in EDA,
  we do not silently discard rows here.
"""

from pathlib import Path
import pandas as pd
import numpy as np

from load import (            # same folder, run from src/data OR use package import
    load_projects,
    load_organizations,
    load_topics,
    load_legal_basis,
)

CLEAN = Path("data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Stage 1: cast money + dates on the projects table
# ----------------------------------------------------------------------
def _to_number(series: pd.Series) -> pd.Series:
    """Coerce a text money column to float, handling European formats.
    Examples handled: '230000', '230000,00', '1.234.567,89', ''."""
    s = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)   # remove thousands separators
        .str.replace(",", ".", regex=False)  # European decimal -> dot
        .replace({"": np.nan, "nan": np.nan})
    )
    return pd.to_numeric(s, errors="coerce")


def clean_projects(df: pd.DataFrame) -> pd.DataFrame:
    p = df.copy()
    # Money
    p["totalCost"] = _to_number(p["totalCost"])
    p["ecMaxContribution"] = _to_number(p["ecMaxContribution"])
    # Dates
    for col in ["startDate", "endDate", "ecSignatureDate"]:
        p[col] = pd.to_datetime(p[col], errors="coerce")
    # Derived: duration in months (guard against missing/negative)
    p["durationMonths"] = (
        (p["endDate"] - p["startDate"]).dt.days / 30.44
    ).round(1)
    p.loc[p["durationMonths"] < 0, "durationMonths"] = np.nan
    # Objective text flag (do not drop yet, just mark)
    p["objectiveLen"] = p["objective"].fillna("").str.len()
    p["hasObjective"] = p["objectiveLen"] > 0
    return p


# ----------------------------------------------------------------------
# Stage 2: collapse organizations into per-project consortium features
# ----------------------------------------------------------------------
def build_consortium_features(orgs: pd.DataFrame) -> pd.DataFrame:
    o = orgs.copy()
    o["ecContribution"] = _to_number(o["ecContribution"])
    o["isCoordinator"] = (o["role"].str.lower() == "coordinator")
    o["isSME"] = (o["SME"].str.lower() == "true")

    g = o.groupby("projectID")
    feats = pd.DataFrame({
        "consortiumSize": g.size(),
        "numCountries": g["country"].nunique(),
        "hasCoordinator": g["isCoordinator"].any(),
        "numSME": g["isSME"].sum(),
        "numHES": g["activityType"].apply(lambda s: (s == "HES").sum()),  # universities
        "numREC": g["activityType"].apply(lambda s: (s == "REC").sum()),  # research orgs
        "numPRC": g["activityType"].apply(lambda s: (s == "PRC").sum()),  # companies
        "numPUB": g["activityType"].apply(lambda s: (s == "PUB").sum()),  # public bodies
    }).reset_index()
    return feats


# ----------------------------------------------------------------------
# Stage 3: collapse topics + legalBasis (one primary each per project)
# ----------------------------------------------------------------------
def build_topic_features(topics: pd.DataFrame) -> pd.DataFrame:
    # Take the first topic per project as the primary topic code.
    t = topics.rename(columns={"topic": "topicCode", "title": "topicTitle"})
    return t.groupby("projectID").first().reset_index()


def build_legalbasis_features(lb: pd.DataFrame) -> pd.DataFrame:
    # First legal basis code per project as the primary programme part.
    l = lb.rename(columns={"legalBasis": "legalBasisCode", "title": "legalBasisTitle"})
    return l.groupby("projectID").first()[["legalBasisCode", "legalBasisTitle"]].reset_index()


# ----------------------------------------------------------------------
# Stage 4: join everything into one clean per-project table
# ----------------------------------------------------------------------
def build_clean_table() -> pd.DataFrame:
    print("Loading raw tables...")
    projects = clean_projects(load_projects())
    consortium = build_consortium_features(load_organizations())
    topics = build_topic_features(load_topics())
    legal = build_legalbasis_features(load_legal_basis())

    print("Joining...")
    df = projects.merge(consortium, left_on="id", right_on="projectID", how="left")
    df = df.merge(topics, left_on="id", right_on="projectID", how="left",
                  suffixes=("", "_t"))
    df = df.merge(legal, left_on="id", right_on="projectID", how="left",
                  suffixes=("", "_l"))

    # Drop the redundant join-key duplicates
    df = df.drop(columns=[c for c in df.columns if c.startswith("projectID")])
    return df


if __name__ == "__main__":
    df = build_clean_table()
    print(f"\nClean table shape: {df.shape}")
    print(f"Projects with objective text: {df['hasObjective'].sum()} / {len(df)}")
    print(f"Median consortium size: {df['consortiumSize'].median()}")
    print(f"Median EC contribution: {df['ecMaxContribution'].median():,.0f} EUR")

    out = CLEAN / "projects_clean.parquet"
    df.to_parquet(out, index=False)
    print(f"\nWrote {out}  ({out.stat().st_size/1e6:.1f} MB)")
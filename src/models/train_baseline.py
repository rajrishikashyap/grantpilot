"""
Phase 2: Model A baseline.

Predict project failure (TERMINATED=1) vs success (CLOSED=0) from
proposal text (TF-IDF) + structured features. LogisticRegression baseline.

This is the BASELINE the LoRA transformer must beat. We evaluate on
minority-class metrics (the 6.6% failures), never raw accuracy.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, roc_auc_score, average_precision_score,
    confusion_matrix, precision_recall_curve,
)

CLEAN = Path("data/clean")

# durationMonths removed: it is mildly lower for TERMINATED (30 vs 24),
# a possible leakage path (end date may record termination). We drop it
# and confirm the score holds, proving the signal is not coming from leakage.
NUMERIC = [
    "ecMaxContribution", "totalCost",
    "consortiumSize", "numCountries", "numSME",
    "numHES", "numREC", "numPRC", "numPUB",
]
CATEGORICAL = ["fundingScheme"]
TEXT = "objective"


def load():
    tr = pd.read_parquet(CLEAN / "model_a_train.parquet")
    te = pd.read_parquet(CLEAN / "model_a_test.parquet")
    # log-transform money (Phase 1 finding: log-normal, raw EUR unusable)
    for d in (tr, te):
        d["ecMaxContribution"] = np.log1p(d["ecMaxContribution"].clip(lower=0))
        d["totalCost"] = np.log1p(d["totalCost"].clip(lower=0))
    return tr, te


def build_model():
    # TF-IDF on text: unigrams+bigrams, cap vocab to keep it light on 8GB RAM
    text_tf = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2),
        min_df=5, stop_words="english", sublinear_tf=True,
    )
    cat_tf = OneHotEncoder(handle_unknown="ignore")

    # Numeric branch: impute missing (the 12 bad durations etc.) then scale.
    num_tf = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])

    pre = ColumnTransformer([
        ("text", text_tf, TEXT),
        ("cat", cat_tf, CATEGORICAL),
        ("num", num_tf, NUMERIC),
    ])

    # LogisticRegression handles sparse TF-IDF natively and is the standard
    # strong baseline for high-dimensional text. class_weight fights the 93/7.
    clf = LogisticRegression(
        max_iter=1000, class_weight="balanced",
        C=1.0, random_state=42,
    )
    return Pipeline([("pre", pre), ("clf", clf)])


def evaluate(model, X_test, y_test):
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    print("\n" + "=" * 55)
    print("BASELINE RESULTS (Model A)")
    print("=" * 55)
    print(f"ROC-AUC:  {roc_auc_score(y_test, proba):.3f}")
    print(f"PR-AUC:   {average_precision_score(y_test, proba):.3f}  "
          f"(baseline = {y_test.mean():.3f} = always-guess-fail rate)")
    print("\nConfusion matrix [rows=true, cols=pred]:")
    print(confusion_matrix(y_test, pred))
    print("\nClassification report:")
    print(classification_report(y_test, pred, target_names=["CLOSED", "TERMINATED"]))


def main():
    tr, te = load()
    X_cols = NUMERIC + CATEGORICAL + [TEXT]
    X_train, y_train = tr[X_cols], tr["label"]
    X_test, y_test = te[X_cols], te["label"]

    print("Training baseline...")
    model = build_model()
    model.fit(X_train, y_train)

    evaluate(model, X_test, y_test)

    # Save the trained baseline and its metrics for comparison vs the transformer.
    Path("models").mkdir(exist_ok=True)
    joblib.dump(model, "models/model_a_baseline.joblib")
    proba = model.predict_proba(X_test)[:, 1]
    metrics = {
        "model": "logreg_tfidf_baseline",
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "pr_auc": round(average_precision_score(y_test, proba), 4),
        "pr_baseline": round(float(y_test.mean()), 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    Path("models/model_a_baseline_metrics.json").write_text(json.dumps(metrics, indent=2))
    print("\nSaved model and metrics to models/")


if __name__ == "__main__":
    main()
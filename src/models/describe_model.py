"""
Introspect the saved Model A pipeline.

Before wrapping Model A as a Reviewer tool, we read its REAL input contract
straight from the fitted pipeline instead of guessing. This prints:
  - the exact input columns the pipeline expects (the frame we must build),
  - each ColumnTransformer branch, so we can SEE whether the money features
    are log-transformed inside the pipeline (if so, we pass raw euros),
  - the total transformed feature count (needed to size the SHAP explainer),
  - the classifier's class order (so we know which column of predict_proba
    is the probability of failure).

Run once from the repo root:
    python -m src.models.describe_model
"""

import json
from pathlib import Path
import joblib

MODEL_PATH = Path("models/model_a_baseline.joblib")
METRICS_PATH = Path("models/model_a_baseline_metrics.json")


def main():
    if not MODEL_PATH.exists():
        raise SystemExit(f"Model file not found at {MODEL_PATH}. "
                         "Run the Phase 2 training that saves it, then retry.")

    pipe = joblib.load(MODEL_PATH)
    print("Loaded object type:", type(pipe).__name__)

    # The exact input columns the pipeline was fit on. This is the single most
    # important line: it is precisely the frame score_proposal must construct.
    if hasattr(pipe, "feature_names_in_"):
        print("\nExpected INPUT columns (feature_names_in_):")
        for c in pipe.feature_names_in_:
            print("  -", c)
    else:
        print("\n(no feature_names_in_ on the pipeline; will infer from the ColumnTransformer)")

    # List the top-level steps.
    print("\nTop-level pipeline steps:")
    try:
        for name, step in pipe.named_steps.items():
            print(f"  '{name}': {type(step).__name__}")
    except AttributeError:
        print("  (not a standard Pipeline)")

    # Find and describe the ColumnTransformer. Sub-pipelines are printed too,
    # which is how a log FunctionTransformer in the numeric branch reveals itself.
    from sklearn.compose import ColumnTransformer
    ct = None
    try:
        for step in pipe.named_steps.values():
            if isinstance(step, ColumnTransformer):
                ct = step
                break
    except AttributeError:
        pass

    if ct is not None:
        print("\nColumnTransformer branches (name -> transformer -> columns):")
        for name, trans, cols in ct.transformers_:
            print(f"  {name}: {type(trans).__name__} on columns {cols}")
            if hasattr(trans, "named_steps"):
                for sn, ss in trans.named_steps.items():
                    print(f"       - {sn}: {type(ss).__name__}")
        try:
            names = ct.get_feature_names_out()
            print(f"\nTotal transformed features: {len(names)}")
            print("First 15 transformed feature names:", list(names[:15]))
        except Exception as e:
            print("get_feature_names_out failed:", e)

    # The final estimator: class order and coefficient shape.
    try:
        clf = list(pipe.named_steps.values())[-1]
        print(f"\nFinal estimator: {type(clf).__name__}")
        if hasattr(clf, "classes_"):
            print("classes_ (index 1 is the 'failure' probability):", clf.classes_)
        if hasattr(clf, "coef_"):
            print("coef_ shape:", clf.coef_.shape)
    except Exception as e:
        print("Could not inspect final estimator:", e)

    if METRICS_PATH.exists():
        print("\nSaved metrics:")
        print(json.dumps(json.loads(METRICS_PATH.read_text()), indent=2))


if __name__ == "__main__":
    main()

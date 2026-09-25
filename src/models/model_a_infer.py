"""
Model A inference and explanation.

Wraps the shipped logistic-regression pipeline (models/model_a_baseline.joblib)
so agents can score a proposal's POST-AWARD RISK (the modelled probability that
a funded project ends TERMINATED rather than CLOSED) and see WHY.

Contract, confirmed by introspecting the fitted pipeline (not guessed):
  input columns (exact order):
    ecMaxContribution, totalCost, consortiumSize, numCountries, numSME,
    numHES, numREC, numPRC, numPUB, fundingScheme, objective
  money columns (ecMaxContribution, totalCost) are NATURAL-LOG transformed
    before the model. The scaler's mean for ecMaxContribution is 13.2, which is
    ln(~550k euros), not raw euros and not log10. So we apply np.log here.
  numeric branch = SimpleImputer(median) + StandardScaler, so any unknown
    numeric feature can be passed as NaN and the model fills it with the
    training median. A draft with no consortium yet still scores.
  classes_ = [0, 1]; risk = predict_proba[:, 1] (probability of failure).
  OneHotEncoder handle_unknown='ignore', so an unseen fundingScheme is safe.

Framing kept from Phase 2: this is POST-AWARD risk, not the award decision.
We report it as risk and never claim it predicts whether a grant is funded.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import joblib

MODEL_PATH = Path("models/model_a_baseline.joblib")

# Exact input columns, in the order the pipeline expects.
INPUT_COLS = [
    "ecMaxContribution", "totalCost", "consortiumSize", "numCountries",
    "numSME", "numHES", "numREC", "numPRC", "numPUB", "fundingScheme", "objective",
]
# Dataset base failure rate (from Model A metrics, pr_baseline). Used to judge
# whether a given risk is high or low RELATIVE to the population, since the
# absolute number is small for almost everything (only ~6.6% ever fail).
BASE_FAILURE_RATE = 0.066

_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        if not MODEL_PATH.exists():
            raise SystemExit(f"Model A not found at {MODEL_PATH}. Train Phase 2 first.")
        _pipe = joblib.load(MODEL_PATH)
    return _pipe


def _log_money(v):
    """Natural-log a euro amount, matching how the model was trained. None or a
    non-positive value becomes NaN, which the pipeline's imputer then fills."""
    if v is None:
        return np.nan
    v = float(v)
    return np.log(v) if v > 0 else np.nan


def _build_frame(objective, fundingScheme, ecMaxContribution=None, totalCost=None,
                 consortiumSize=None, numCountries=None, numSME=None, numHES=None,
                 numREC=None, numPRC=None, numPUB=None):
    """Build the exact one-row frame the pipeline expects."""
    def _num(v):
        return np.nan if v is None else float(v)

    row = {
        "ecMaxContribution": _log_money(ecMaxContribution),
        "totalCost": _log_money(totalCost),
        "consortiumSize": _num(consortiumSize),
        "numCountries": _num(numCountries),
        "numSME": _num(numSME),
        "numHES": _num(numHES),
        "numREC": _num(numREC),
        "numPRC": _num(numPRC),
        "numPUB": _num(numPUB),
        "fundingScheme": "" if fundingScheme is None else str(fundingScheme),
        "objective": "" if objective is None else str(objective),
    }
    return pd.DataFrame([row], columns=INPUT_COLS)


def score_proposal(objective, fundingScheme, **numeric):
    """Return Model A's post-award failure risk for one proposal."""
    pipe = _load()
    df = _build_frame(objective, fundingScheme, **numeric)
    risk = float(pipe.predict_proba(df)[0, 1])
    return {
        "risk": risk,                                 # P(TERMINATED)
        "base_rate": BASE_FAILURE_RATE,
        "relative_to_base": risk / BASE_FAILURE_RATE,
        "predicted_label": int(risk >= 0.5),
    }


def _clean_name(raw):
    """Turn a transformed feature name into something a human reads.
    'text__quantum' -> 'word:quantum'; 'cat__fundingScheme_RIA' -> 'scheme:RIA';
    'num__ecMaxContribution' -> 'ecMaxContribution'."""
    if raw.startswith("text__"):
        return f"word:{raw[len('text__'):]}"
    if raw.startswith("cat__fundingScheme_"):
        return f"scheme:{raw[len('cat__fundingScheme_'):]}"
    if raw.startswith("cat__"):
        return raw[len("cat__"):]
    if raw.startswith("num__"):
        return raw[len("num__"):]
    return raw


def explain_proposal(objective, fundingScheme, top_k=8, **numeric):
    """
    Explain one prediction.

    The model is linear, so the SHAP value of feature i is
    coef_i * (x_i - E[x_i]). With an empty-proposal / average-budget baseline
    (E[x_i] = 0 in the transformed space), that is exactly coef_i * x_i, which
    we compute here in closed form: no sampling, no approximation. Positive
    contributions push the prediction toward failure (risk); negative
    contributions push toward success.
    """
    pipe = _load()
    pre = pipe.named_steps["pre"]
    clf = pipe.named_steps["clf"]

    df = _build_frame(objective, fundingScheme, **numeric)
    x = pre.transform(df)
    x = x.toarray()[0] if hasattr(x, "toarray") else np.asarray(x)[0]
    names = pre.get_feature_names_out()
    contrib = clf.coef_[0] * x     # exact linear SHAP with a zero baseline

    order = np.argsort(contrib)
    top_protective = [(_clean_name(names[i]), float(contrib[i]))
                      for i in order[:top_k] if contrib[i] < 0]
    top_risk = [(_clean_name(names[i]), float(contrib[i]))
                for i in order[::-1][:top_k] if contrib[i] > 0]

    risk = float(pipe.predict_proba(df)[0, 1])
    return {
        "risk": risk,
        "top_risk_drivers": top_risk,
        "top_protective_drivers": top_protective,
    }


if __name__ == "__main__":
    # Direct check, no agent. Run: python -m src.models.model_a_infer
    obj = ("This project develops an AI platform for early cancer detection from "
           "medical imaging, validated across three hospitals, with an open dataset "
           "and clinical trial protocol.")
    print(score_proposal(obj, "RIA", ecMaxContribution=5_000_000, totalCost=6_000_000,
                         consortiumSize=8, numCountries=5))
    exp = explain_proposal(obj, "RIA", ecMaxContribution=5_000_000, totalCost=6_000_000,
                           consortiumSize=8, numCountries=5, top_k=6)
    print("risk:", exp["risk"])
    print("risk drivers:", exp["top_risk_drivers"])
    print("protective:", exp["top_protective_drivers"])

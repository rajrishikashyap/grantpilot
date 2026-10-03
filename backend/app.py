"""
GrantPilot API.

Thin FastAPI wrapper over the deterministic pipeline. Every quantitative
judgment lives in the tool code under src/; this layer just exposes it over
HTTP and lets the React frontend call it. Only /assess touches the local LLM.

Run from the repo root:
    uvicorn backend.app:app --reload --port 8000
Swagger UI at http://localhost:8000/docs
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import ProposalIn, EligibilityIn, BudgetIn, RiskIn, SearchIn

from src.agents.eligibility_agent import check_eligibility
from src.models.train_model_b import score_budget
from src.models.model_a_infer import score_proposal, explain_proposal
from src.rag.search_api import search_records
from src.agents.pipeline import run_pipeline

app = FastAPI(title="GrantPilot API", version="1.0")

# Open CORS: the frontend runs on a different port (Vite dev) and host (deploy).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATS_PATH = Path("models/grant_stats.json")
_stats_cache = None


def _model_a_numeric(body):
    """Map the API's snake_case fields to Model A's camelCase input names."""
    return {
        "ecMaxContribution": body.ec_contribution,
        "totalCost": body.total_cost,
        "consortiumSize": body.consortium_size,
        "numCountries": body.num_countries,
        "numSME": body.num_sme,
        "numHES": body.num_hes,
        "numREC": body.num_rec,
        "numPRC": body.num_prc,
        "numPUB": body.num_pub,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/eligibility")
def eligibility(body: EligibilityIn):
    return check_eligibility(
        scheme=body.scheme,
        ec_contribution=body.ec_contribution,
        consortium_size=body.consortium_size,
        num_countries=body.num_countries,
    )


@app.post("/budget")
def budget(body: BudgetIn):
    return score_budget(scheme=body.scheme, ec_contribution=body.ec_contribution)


@app.post("/risk")
def risk(body: RiskIn):
    numeric = _model_a_numeric(body)
    base = score_proposal(objective=body.idea, fundingScheme=body.scheme, **numeric)
    drivers = explain_proposal(
        objective=body.idea, fundingScheme=body.scheme, top_k=8, **numeric
    )
    return {**base, **drivers}


@app.post("/search")
def search(body: SearchIn):
    """Structured precedent search: a list of grant records the UI renders as cards."""
    return {
        "query": body.query,
        "k": body.k,
        "results": search_records(body.query, body.k),
    }


@app.get("/stats")
def stats():
    """Precomputed CORDIS analytics for the dashboard (see src/data/compute_stats.py)."""
    global _stats_cache
    if _stats_cache is None:
        if not STATS_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail="Stats not computed. Run: python -m src.data.compute_stats",
            )
        _stats_cache = json.loads(STATS_PATH.read_text())
    return _stats_cache


@app.post("/assess")
def assess(body: ProposalIn):
    """Full multi-agent run. Uses the local LLM, so it can fail if Ollama is down."""
    proposal = {
        "id": body.id,
        "idea": body.idea,
        "scheme": body.scheme,
        "ec_contribution": body.ec_contribution,
        "total_cost": body.total_cost,
        "consortium_size": body.consortium_size,
        "num_countries": body.num_countries,
        "num_sme": body.num_sme,
        "num_hes": body.num_hes,
        "num_rec": body.num_rec,
        "num_prc": body.num_prc,
        "num_pub": body.num_pub,
    }
    try:
        return run_pipeline(proposal, max_iters=2, verbose=False)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Assessment failed (likely LLM unreachable): {e}",
        )

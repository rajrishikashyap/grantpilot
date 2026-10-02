"""
The GrantPilot FastAPI backend.

Wraps the pipeline and its deterministic cores as HTTP endpoints so the Phase 6
frontend (and anyone with curl) can use the system over the network. The design
mirrors the whole project's spine:

  - The DETERMINISTIC endpoints (/eligibility, /budget, /risk, /search) are fast
    and safe to deploy anywhere. They call the same cores the agents use.
  - /assess runs the full pipeline, including the quality loop, which calls the
    local LLM (Ollama). It is slow and needs Ollama running.

Models load lazily on first use (Model A on the first /risk or /assess, the
embedding model + Chroma on the first /search or /assess), so the server starts
quickly and only pays the load cost when a relevant endpoint is first hit.

Run locally from the repo root:
    pip install fastapi "uvicorn[standard]"
    uvicorn backend.app:app --reload --port 8000
Then open http://localhost:8000/docs for an interactive test page.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import ProposalIn, EligibilityIn, BudgetIn, RiskIn, SearchIn

from src.agents.eligibility_agent import check_eligibility
from src.models.train_model_b import score_budget
from src.models.model_a_infer import score_proposal, explain_proposal
from src.rag.search import search_grants
from src.agents.pipeline import run_pipeline


app = FastAPI(
    title="GrantPilot API",
    version="0.1.0",
    description="Multi-agent grant-writing and compliance copilot over EU CORDIS data.",
)

# CORS: the frontend is served from a different origin (Vite dev server, then
# Vercel/Netlify), so the browser needs permission to call this API. Open for
# development; tighten allow_origins to the deployed frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _model_a_numeric(body):
    """Map the API's snake_case fields to Model A's internal column names.
    One place, so the naming contract lives here and nowhere else."""
    return dict(
        ecMaxContribution=body.ec_contribution,
        totalCost=body.total_cost,
        consortiumSize=body.consortium_size,
        numCountries=body.num_countries,
        numSME=body.num_sme,
        numHES=body.num_hes,
        numREC=body.num_rec,
        numPRC=body.num_prc,
        numPUB=body.num_pub,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "grantpilot"}


@app.post("/eligibility")
def eligibility(body: EligibilityIn):
    """Deterministic. Three-way verdict ELIGIBLE / NOT ELIGIBLE / UNDETERMINED."""
    return check_eligibility(
        scheme=body.scheme,
        ec_contribution=body.ec_contribution,
        consortium_size=body.consortium_size,
        num_countries=body.num_countries,
    )


@app.post("/budget")
def budget(body: BudgetIn):
    """Deterministic. Model B per-scheme budget anomaly."""
    return score_budget(body.scheme, body.ec_contribution)


@app.post("/risk")
def risk(body: RiskIn):
    """Deterministic. Model A post-award risk + SHAP drivers for an objective."""
    numeric = _model_a_numeric(body)
    s = score_proposal(body.objective, body.scheme, **numeric)
    e = explain_proposal(body.objective, body.scheme, top_k=6, **numeric)
    return {
        **s,
        "top_risk_drivers": e["top_risk_drivers"],
        "top_protective_drivers": e["top_protective_drivers"],
    }


@app.post("/search")
def search(body: SearchIn):
    """Semantic search over 35k CORDIS objectives (RAG). Returns a text block."""
    return {"query": body.query, "k": body.k,
            "results": search_grants(body.query, k=body.k)}


@app.post("/assess")
def assess(body: ProposalIn):
    """
    Full pipeline: eligibility gate, budget, quality loop (drafting + revision),
    advisory risk. SLOW: the quality loop calls the local LLM. Requires Ollama
    running with the qwen2.5:3b model pulled.
    """
    try:
        report = run_pipeline(body.model_dump(), verbose=False)
    except Exception as exc:
        # Most likely cause in practice: Ollama not running / model not pulled.
        raise HTTPException(
            status_code=503,
            detail=(f"Assessment failed, likely the local LLM is unreachable. "
                    f"Is Ollama running with qwen2.5:3b pulled? ({exc})"),
        )
    return report

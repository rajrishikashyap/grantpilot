"""
Pydantic request models for the GrantPilot API.

These do two jobs: they document exactly what each endpoint accepts (FastAPI
turns them into the interactive /docs page), and they validate incoming JSON
before it reaches the pipeline, so a bad request fails fast with a clear 422
instead of blowing up inside the model code.

Field names are the snake_case the pipeline already uses (ec_contribution,
consortium_size, ...). The mapping to Model A's internal column names
(ecMaxContribution, consortiumSize, ...) happens in app.py, in one place.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ProposalIn(BaseModel):
    """A full proposal, for the /assess pipeline."""
    id: str = "proposal"
    idea: str = Field(..., description="One or two sentences describing the research idea")
    scheme: str = Field(..., description="EU funding scheme, e.g. RIA, IA, ERC-STG")
    ec_contribution: Optional[float] = None
    total_cost: Optional[float] = None
    consortium_size: Optional[int] = None
    num_countries: Optional[int] = None
    num_sme: Optional[int] = None
    num_hes: Optional[int] = None
    num_rec: Optional[int] = None
    num_prc: Optional[int] = None
    num_pub: Optional[int] = None


class EligibilityIn(BaseModel):
    scheme: str
    ec_contribution: Optional[float] = None
    consortium_size: Optional[int] = None
    num_countries: Optional[int] = None


class BudgetIn(BaseModel):
    scheme: str
    ec_contribution: float


class RiskIn(BaseModel):
    """Score an OBJECTIVE text directly (Model A), with optional structured features."""
    objective: str
    scheme: str
    ec_contribution: Optional[float] = None
    total_cost: Optional[float] = None
    consortium_size: Optional[int] = None
    num_countries: Optional[int] = None
    num_sme: Optional[int] = None
    num_hes: Optional[int] = None
    num_rec: Optional[int] = None
    num_prc: Optional[int] = None
    num_pub: Optional[int] = None


class SearchIn(BaseModel):
    query: str
    k: int = 5

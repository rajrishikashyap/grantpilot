"""
The Reviewer agent: scores a draft proposal like a review panel, using Model A.

Design choice that matters, and is the same lesson the Budget agent's dropped
zero taught us: the agent does NOT retype the proposal's objective into a tool
call. Making a 3B model copy a long objective (or a precise number) through an
Action Input is fragile. Instead proposals are registered by id, and the agent
passes only a short proposal_id. The tool looks up the real fields and runs
Model A. This is also exactly how the Phase 4 Coordinator will hand a proposal
to the Reviewer: by reference, not by re-typing.

Framing: Model A predicts POST-AWARD risk (will a funded project end
TERMINATED), not the award decision. The role says so, so the agent does not
overclaim that a low risk means the proposal will be funded.
"""

from src.models.model_a_infer import score_proposal, explain_proposal
from src.agents.tools import Tool
from src.agents.base import Agent


# In-memory proposal store. The test registers proposals here; in Phase 4 the
# Coordinator will register them before invoking the Reviewer.
PROPOSALS = {}


def register_proposal(proposal_id, **fields):
    """Store a proposal's fields (objective, fundingScheme, and any numeric
    features like ecMaxContribution) under an id the agent can reference."""
    PROPOSALS[proposal_id] = fields


REVIEWER_ROLE = (
    "You are a grant Reviewer, acting like a funding review panel. "
    "You assess a proposal's POST-AWARD risk: the modelled probability that a "
    "funded project would end up terminated rather than completed. This is a "
    "risk signal, not a prediction of whether the proposal will be awarded. "
    "Call assess_proposal with the given proposal_id. The tool returns a computed "
    "verdict (LOW, MODERATE or HIGH), the risk probability, the driving factors, "
    "and sometimes a NOTE about scheme-dominated risk. "
    "Give a Final Answer that reports the verdict and risk probability exactly as "
    "the tool gave them (do not recompute or change them), explains two or three "
    "of the strongest factors in plain language for a human panel, and, if the "
    "tool included a NOTE, states that caveat. Never invent a score, and never "
    "claim the model predicts the funding decision."
)


def _fmt_drivers(drivers):
    return ", ".join(f"{name} ({val:+.2f})" for name, val in drivers) or "none"


def make_review_tool():
    def _run(args):
        pid = args.get("proposal_id")
        if pid is None:
            return 'Error: assess_proposal needs {"proposal_id": "<id>"}.'
        if pid not in PROPOSALS:
            return (f"Error: no proposal registered with id '{pid}'. "
                    f"Known ids: {list(PROPOSALS)}.")
        fields = PROPOSALS[pid]
        s = score_proposal(**fields)
        e = explain_proposal(top_k=6, **fields)

        # Compute the verdict band deterministically, so the agent narrates it
        # rather than judging it (a 3B model judges thresholds unreliably).
        xb = s["relative_to_base"]
        if xb < 1.5:
            verdict = "LOW"
        elif xb <= 4.0:
            verdict = "MODERATE"
        else:
            verdict = "HIGH"

        # Compute scheme dominance deterministically too: is the single largest
        # risk factor a scheme factor that outweighs the next factor at least 2x?
        # If so, the risk mostly reflects the scheme's base termination rate.
        risk_drivers = e["top_risk_drivers"]
        note = ""
        if risk_drivers:
            top_name, top_val = risk_drivers[0]
            next_val = abs(risk_drivers[1][1]) if len(risk_drivers) > 1 else 0.0
            if top_name.startswith("scheme:") and abs(top_val) >= 2.0 * max(next_val, 1e-9):
                note = (f"NOTE: this risk is dominated by the funding-scheme factor "
                        f"({top_name}), so it mainly reflects that scheme's historical "
                        f"termination base rate, not this proposal's content.")

        text = (
            f"proposal {pid} | verdict: {verdict} | post-award failure risk: "
            f"{s['risk']*100:.1f}% ({xb:.1f}x the {s['base_rate']*100:.1f}% base rate)\n"
            f"top risk-raising factors: {_fmt_drivers(risk_drivers)}\n"
            f"top protective factors: {_fmt_drivers(e['top_protective_drivers'])}"
        )
        if note:
            text += "\n" + note
        return text

    return Tool(
        name="assess_proposal",
        description=(
            "Assess a registered proposal's post-award failure risk with Model A, "
            "returning the risk probability and the factors driving it. "
            'Action Input must be JSON like {"proposal_id": "P1"}.'
        ),
        func=_run,
    )


def make_reviewer_agent():
    tool = make_review_tool()
    return Agent(
        name="ReviewerAgent",
        role=REVIEWER_ROLE,
        registry={tool.name: tool},
        max_steps=5,
    )

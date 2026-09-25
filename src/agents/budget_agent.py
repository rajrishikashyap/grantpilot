"""
The Budget agent: the first real GrantPilot agent.

It wraps Model B (the per-scheme budget-anomaly detector from Phase 2) as a
single tool, gives the ReAct engine a budget-reviewer role, and lets the
agent decide when to call the tool and how to phrase the verdict.

This is the simplest of the five agents on purpose: one tool, one clear job.
It establishes the pattern every other agent follows. Note what it does NOT
do: it does not reimplement any budget logic. Model B already computed the
per-scheme robust z-score in Phase 2; the agent just calls it and reasons
about the result. The ML lives in the model, the orchestration lives in the
agent, and they meet at the tool boundary.
"""

from src.models.train_model_b import score_budget
from src.agents.tools import Tool
from src.agents.base import Agent


# The role. This is the entire "personality" of the Budget agent. It tells the
# model its job, forbids guessing (the whole point is to use the real model),
# and specifies what a good Final Answer looks like.
BUDGET_ROLE = (
    "You are the Budget Compliance reviewer in a grant-writing system. "
    "Given a proposal's funding scheme and its requested EU contribution in euros, "
    "your job is to judge whether that budget is normal or unusual for that scheme. "
    "You must call the score_budget tool to get the statistical assessment. "
    "Never estimate or guess a verdict from your own knowledge; the tool is the "
    "authority. "
    "Call score_budget once, with the exact scheme and euro amount from the task. "
    "If the tool returns a score, give a Final Answer that states a clear verdict "
    "(NORMAL or ANOMALOUS), the robust z-score, and one plain-English sentence a "
    "human reviewer could act on. "
    "If the tool reports that it cannot score the budget (for example an unknown "
    "scheme, or too few funded examples), your Final Answer must state that you "
    "cannot assess this budget because the scheme is not recognised. In that case "
    "you must NOT call the tool again with a different scheme, must NOT compare "
    "against any other scheme, and must NOT guess a verdict. A scheme you cannot "
    "score is unassessable, full stop."
)


def make_budget_tool():
    """
    Wrap score_budget(scheme, ec_contribution) -> dict as a ReAct Tool that
    takes the args dict from the parser and returns a readable string. We
    flatten Model B's dict into text because the engine feeds Observations
    back to the model as text, and a clean sentence reasons better than a
    raw dict dump.
    """
    def _run(args):
        scheme = args.get("scheme")
        ec = args.get("ec_contribution")
        if scheme is None or ec is None:
            return ('Error: score_budget needs both fields, like '
                    '{"scheme": "ERC-STG", "ec_contribution": 1500000}.')
        try:
            ec = float(ec)
        except (TypeError, ValueError):
            return f"Error: ec_contribution must be a number, got {ec!r}."

        result = score_budget(scheme, ec)

        # Model B returns scored=False when it has no stats for the scheme.
        if not result.get("scored"):
            return f"Could not score: {result.get('reason', 'unknown reason')}"

        return (
            f"scheme: {result['scheme']} | "
            f"requested budget: {result['budget_eur']:,.0f} EUR | "
            f"scheme median: {result['scheme_median_eur']:,} EUR | "
            f"robust z-score: {result['robust_z']} | "
            f"anomaly: {result['is_anomaly']}\n"
            f"{result['explanation']}"
        )

    return Tool(
        name="score_budget",
        description=(
            "Judge whether a requested budget is unusual for its EU funding scheme, "
            "using a per-scheme robust z-score model built from 35,000 real grants. "
            'Action Input must be JSON like {"scheme": "ERC-STG", "ec_contribution": 1500000}. '
            "Returns the requested budget, the scheme median, the robust z-score, an "
            "anomaly flag, and a plain-English explanation."
        ),
        func=_run,
    )


def make_budget_agent():
    """Build the Budget agent: the budget role plus the score_budget tool."""
    tool = make_budget_tool()
    return Agent(
        name="BudgetAgent",
        role=BUDGET_ROLE,
        registry={tool.name: tool},
        max_steps=5,
    )

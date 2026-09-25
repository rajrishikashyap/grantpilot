"""
Reviewer agent isolation test.

Two stages:
  STAGE 1 (no LLM): call score_proposal / explain_proposal directly on two
  contrasting proposals and print the risk plus the driving factors. This is
  the inspect-do-not-trust step: read what Model A actually says before letting
  an agent narrate it. Do NOT assume which proposal is riskier; report what the
  model returns.

  STAGE 2 (LLM): register the proposals, then have the Reviewer agent assess
  each by id. The agent should call assess_proposal, then write a panel-style
  verdict grounded in the risk score and factors, without retyping the
  objective and without claiming it predicts the award decision.

Run from the repo root:
    python -m src.agents.test_reviewer_agent
"""

from src.models.model_a_infer import score_proposal, explain_proposal
from src.agents.reviewer_agent import register_proposal, make_reviewer_agent


# Two contrasting proposals. We are NOT asserting which is riskier; the model
# decides. P1 is a large collaborative applied project; P2 is a small single
# fellowship. They also exercise both paths: P1 supplies consortium numbers,
# P2 leaves them unknown (the imputer fills them).
P1 = dict(
    objective=(
        "The project develops and clinically validates an AI platform for early "
        "cancer detection from histopathology images across a consortium of "
        "hospitals, delivering an open benchmark dataset, a certified software "
        "pipeline, and a prospective clinical trial protocol for regulatory review."
    ),
    fundingScheme="RIA",
    ecMaxContribution=5_000_000,
    totalCost=6_200_000,
    consortiumSize=9,
    numCountries=6,
    numSME=3,
    numHES=3,
    numREC=2,
    numPRC=1,
    numPUB=0,
)

P2 = dict(
    objective=(
        "This individual fellowship investigates code-switching patterns in "
        "multilingual classroom discourse, combining corpus analysis with "
        "classroom observation to produce a descriptive grammar of teacher "
        "language alternation."
    ),
    fundingScheme="MSCA-IF",
    ecMaxContribution=200_000,
    totalCost=200_000,
    # consortium features left unknown on purpose: a single fellowship has none.
)


def stage1_direct():
    print("#" * 70)
    print("# STAGE 1: direct Model A scoring (no LLM)")
    print("#" * 70)
    for name, p in [("P1", P1), ("P2", P2)]:
        s = score_proposal(**p)
        e = explain_proposal(top_k=6, **p)
        print(f"\n=== {name} ({p['fundingScheme']}) ===")
        print(f"post-award failure risk: {s['risk']*100:.2f}%  "
              f"({s['relative_to_base']:.2f}x the 6.6% base rate)")
        print("top risk-raising factors:", e["top_risk_drivers"])
        print("top protective factors:", e["top_protective_drivers"])


def stage2_agent():
    print("\n" + "#" * 70)
    print("# STAGE 2: the Reviewer agent assesses each proposal by id")
    print("#" * 70)
    register_proposal("P1", **P1)
    register_proposal("P2", **P2)

    agent = make_reviewer_agent()
    for pid in ["P1", "P2"]:
        answer = agent.run(f"Review the proposal with id {pid}.", verbose=True)
        print("\n" + "-" * 70)
        print(f"{pid} REVIEW:\n{answer}")


if __name__ == "__main__":
    stage1_direct()
    stage2_agent()

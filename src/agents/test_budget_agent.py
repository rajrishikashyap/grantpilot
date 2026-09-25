"""
Budget agent isolation test.

Three cases, chosen to exercise the whole path:
  1. A budget that should look NORMAL for its scheme.
  2. A budget that should look ANOMALOUS (far above the scheme's norm).
  3. An UNKNOWN scheme, so we see the agent handle a "could not score"
     result gracefully instead of inventing a verdict.

We phrase each case in natural language, as a real proposal review would
arrive, so we also test that the agent can pull the scheme and the number
out of a sentence and pass them to the tool correctly.

Run from the repo root:
    python -m src.agents.test_budget_agent
"""

from src.agents.budget_agent import make_budget_agent


def main():
    agent = make_budget_agent()

    cases = [
        # ERC-STG grants are typically capped near 1.5M EUR, so this should
        # read as normal for the scheme.
        "A proposal under the ERC-STG scheme is requesting 1,500,000 EUR. "
        "Is that budget normal for this scheme?",

        # Far above any ERC-STG norm: should be flagged anomalous.
        "A proposal under the ERC-STG scheme is requesting 45,000,000 EUR. "
        "Is that budget normal for this scheme?",

        # A scheme the model has no stats for: the tool returns 'could not
        # score', and the agent should report that honestly, not guess.
        "A proposal under the scheme MADE-UP-SCHEME is requesting 2,000,000 EUR. "
        "Is that budget normal for this scheme?",
    ]

    for i, task in enumerate(cases, 1):
        print("\n" + "#" * 70)
        print(f"# CASE {i}")
        print("#" * 70)
        answer = agent.run(task, verbose=True)
        print("\n" + "-" * 70)
        print(f"CASE {i} VERDICT:\n{answer}")


if __name__ == "__main__":
    main()

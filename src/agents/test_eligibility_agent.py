"""
Eligibility agent isolation test.

Four cases, chosen to hit every branch of the rules:
  E1: RIA with 9 partners across 6 countries      -> ELIGIBLE
  E2: RIA with 1 partner in 1 country             -> NOT ELIGIBLE (too small)
  E3: ERC-STG requesting 2.5M EUR                  -> NOT ELIGIBLE (over 1.5M cap)
  E4: scheme "MADE-UP"                             -> rules not on file

We also leave one value unknown in E1 style elsewhere if needed, but the tool
already reports UNCHECKED for anything missing, so the agent must flag it.

Run from the repo root:
    python -m src.agents.test_eligibility_agent
"""

from src.agents.eligibility_agent import register_proposal, make_eligibility_agent


def main():
    register_proposal("E1", scheme="RIA", ec_contribution=5_000_000,
                      consortium_size=9, num_countries=6)
    register_proposal("E2", scheme="RIA", ec_contribution=800_000,
                      consortium_size=1, num_countries=1)
    register_proposal("E3", scheme="ERC-STG", ec_contribution=2_500_000,
                      consortium_size=1)
    register_proposal("E4", scheme="MADE-UP", ec_contribution=1_000_000,
                      consortium_size=4, num_countries=4)

    agent = make_eligibility_agent()
    for pid in ["E1", "E2", "E3", "E4"]:
        print("\n" + "#" * 70)
        print(f"# {pid}")
        print("#" * 70)
        answer = agent.run(f"Check eligibility for the proposal with id {pid}.",
                           verbose=True)
        print("\n" + "-" * 70)
        print(f"{pid} RESULT:\n{answer}")


if __name__ == "__main__":
    main()

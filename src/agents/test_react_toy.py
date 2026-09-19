"""
3A smoke test: prove the ReAct engine works end to end on toy tools.

We ask a question that CANNOT be answered without calling tools:
  - The city facts are hard-coded and not in the model's training data, so
    the model must call city_lookup to get them.
  - The arithmetic combines those looked-up numbers, so the model should
    call calculator rather than trust its own (unreliable) mental math.

If the final answer is correct, the loop genuinely routed data from a tool,
through the model, into a second tool, and back. That is the whole cycle
working. If it is wrong, the verbose trace shows you exactly which beat
broke: a bad parse, a wrong tool choice, or a hallucinated observation.

Run from the repo root so the package imports resolve:
    python -m src.agents.test_react_toy
"""

from .react import run_agent
from .tools import TOY_TOOLS


def main():
    # This question forces: two city_lookup calls, then a calculator call.
    question = (
        "What is the combined population of Zephyria and Marrowfen? "
        "Use the tools to find each city's population, then add them."
    )

    print("QUESTION:")
    print(question)

    answer = run_agent(question, TOY_TOOLS, max_steps=8, verbose=True)

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(answer)

    # Ground truth for you to check against: 812000 + 47000 = 859000.
    print("\n(Expected combined population: 859000)")


if __name__ == "__main__":
    main()

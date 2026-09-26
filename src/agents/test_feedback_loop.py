"""
Feedback loop isolation test.

Runs the draft -> score -> revise -> re-score loop on one proposal and prints
each iteration's text-risk and draft, then the before/after.

Read it critically for the finding, not just the number:
  - Did text-risk actually go down across iterations?
  - AND did the revision preserve the proposal's substance, or did it strip
    essential topic words to game the score? Look at whether words like
    "disease" survived in a crop-disease proposal. Lower text-risk that
    degrades the proposal is a caution, not a win.

Run from the repo root (this makes several local LLM calls, so it is slow):
    python -m src.agents.test_feedback_loop
"""

from src.agents.feedback_loop import improve_draft


def main():
    idea = ("A platform using machine learning on low-cost drone imagery to "
            "detect early-stage crop disease in smallholder farms, with an "
            "offline mobile app so farmers get advice without reliable internet.")
    scheme = "RIA"
    numeric = dict(ecMaxContribution=5_000_000, totalCost=6_200_000,
                   consortiumSize=9, numCountries=6)

    result = improve_draft(idea, scheme, max_iters=2, top_words=6,
                           verbose=True, **numeric)

    print("\n" + "=" * 70)
    print("MARGINAL TEXT RISK ACROSS ITERATIONS (percentage points)")
    print("=" * 70)
    for i, score, _ in result["history"]:
        print(f"  iteration {i}: {score*100:.3f} pp")
    print(f"\nbest (lowest) marginal text risk: {result['best_text_risk']*100:.3f} pp")

    print("\n" + "=" * 70)
    print("FIRST DRAFT")
    print("=" * 70)
    print(result["history"][0][2])

    print("\n" + "=" * 70)
    print("BEST DRAFT (lowest text-risk)")
    print("=" * 70)
    print(result["best_draft"])


if __name__ == "__main__":
    main()

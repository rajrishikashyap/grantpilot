"""
Quality loop isolation test.

Runs draft -> quality-check -> revise-for-gaps -> re-check on one proposal and
prints the checks passed and the remaining gaps per iteration, the final draft,
and the advisory Model A risk.

Read it for two things:
  1. Did the checks-passed count go UP across iterations (the loop closing gaps)?
  2. Did the revision PRESERVE substance while adding the missing pieces, or did
     it pad with filler? The whole point of the quality pivot is that the loop
     has a job it can actually do without degrading the proposal.

The advisory risk is shown but is NOT what the loop optimises; after 4A we know
optimising it is counterproductive, so here it is context only.

Run from the repo root (several local LLM calls, slow on the GTX 1650):
    python -m src.agents.test_quality_loop
"""

from src.agents.quality_loop import improve_draft_quality


def _print_checks(q):
    for label, passed, detail in q["checks"]:
        mark = "PASS" if passed else "GAP "
        print(f"    [{mark}] {label} ({detail})")


def main():
    idea = ("A platform using machine learning on low-cost drone imagery to "
            "detect early-stage crop disease in smallholder farms, with an "
            "offline mobile app so farmers get advice without reliable internet.")
    scheme = "RIA"
    numeric = dict(ecMaxContribution=5_000_000, totalCost=6_200_000,
                   consortiumSize=9, numCountries=6)

    result = improve_draft_quality(idea, scheme, max_iters=2, verbose=True,
                                   **numeric)

    print("\n" + "=" * 70)
    print("QUALITY CHECKS ACROSS ITERATIONS")
    print("=" * 70)
    for i, passed, total, gaps, _ in result["history"]:
        print(f"  iteration {i}: {passed}/{total} passed, gaps: {gaps}")

    print("\n" + "=" * 70)
    print("FINAL DRAFT (most checks passed)")
    print("=" * 70)
    print(result["best_draft"])

    print("\n" + "=" * 70)
    print("FINAL QUALITY DETAIL")
    print("=" * 70)
    _print_checks(result["best_quality"])

    print("\n" + "=" * 70)
    print("ADVISORY RISK (context only, not optimised)")
    print("=" * 70)
    a = result["advisory_risk"]
    print(f"  post-award risk: {a['risk']*100:.2f}% ({a['relative_to_base']:.2f}x base)")
    print(f"  marginal text risk: {a['text_risk']*100:.3f} pp")
    print(f"  top risk words: {[w for w, _ in a['risk_words']]}")


if __name__ == "__main__":
    main()

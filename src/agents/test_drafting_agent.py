"""
Drafting agent isolation test.

One research idea, run end to end: the agent should call search_grants to pull
real funded precedents, then write a Concept and Objectives section grounded in
them. We print the full trace so you can watch the retrieve-then-generate cycle,
then the cleaned draft.

Read the draft critically for two things:
  1. Did retrieval actually shape it (does it echo framing/vocabulary from the
     kind of funded work in this area), or did the model ignore the search
     results and free-associate?
  2. Is it original, not copied sentences from the retrieved objectives?

A 3B model will not write a fundable section. The point here is the pipeline:
retrieval grounding + generation in one loop, with the house dash rule enforced.

Run from the repo root:
    python -m src.agents.test_drafting_agent
"""

from src.agents.drafting_agent import draft_section


def main():
    idea = (
        "A platform that uses machine learning on low-cost drone imagery to "
        "detect early-stage crop disease in smallholder farms, with an offline "
        "mobile app so farmers get advice without reliable internet."
    )
    scheme = "RIA"

    print("IDEA:", idea)
    print("SCHEME:", scheme)

    draft = draft_section(idea, scheme, verbose=True)

    print("\n" + "=" * 70)
    print("CLEANED DRAFT (house dash rule applied)")
    print("=" * 70)
    print(draft)


if __name__ == "__main__":
    main()

"""
Phase 4 eval harness (4C).

Runs several proposals through the deterministic pipeline and measures whether
the quality loop actually HELPS, and does so without degrading the proposal. It
deliberately measures SUBSTANCE, not just whether checks flipped to PASS, which
is the whole lesson from the risk-loop and Goodhart findings.

Per proposal it reports:
  eligibility     - the gate verdict (gated proposals skip the rest)
  content 0 -> f  - content checks passed at the first draft vs the final draft
                    (did the loop close real gaps?)
  revisions       - how many revision passes it took
  retention       - fraction of the first draft's distinctive content words that
                    survive in the final draft (substance preserved? ~1.0 is good,
                    low means the revision threw content away)
  leak            - did an instruction/label phrase leak into the final draft?
                    (the Goodhart failure mode; should be False)
  len             - final word count (should sit in the length band)
  risk            - advisory Model A risk band + marginal text risk (context only)

Then an aggregate summary. This is what lets you SAY, in an interview, what the
system does and does not do.

Run from the repo root (each eligible proposal runs the local LLM loop, so this
is slow, budget a few minutes):
    python -m eval.eval_pipeline
"""

import re

from src.agents.pipeline import run_pipeline
from src.agents.quality_loop import check_quality


_STOP = set("the a an and or of to in on for with this that these those is are was "
            "will our their its from by as at be can also into within more using "
            "use used which such other than then they them it we".split())


def _content_words(text):
    """Distinctive content words: alphabetic, length >= 5, not a stopword."""
    return {w.lower() for w in re.findall(r"[A-Za-z]{5,}", text or "")} - _STOP


def _instruction_leak(text):
    """True if an instruction or gap-label phrase leaked into the draft."""
    low = (text or "").lower()
    phrases = [
        "explicitly mention", "methodology or validation", "impact or dissemination",
        "numbered objective must", "gaps you must fix", "note about what to include",
        "revised section", "labelled section",
    ]
    return any(p in low for p in phrases)


def evaluate_one(proposal):
    r = run_pipeline(proposal, verbose=False)
    row = {"id": r["id"], "scheme": r["scheme"],
           "eligibility": r["eligibility"].get("verdict", "UNDETERMINED")}

    if r.get("gated"):
        row["gated"] = True
        return row
    row["gated"] = False

    q = r["quality"]
    first, final = q["first_draft"], q["final_draft"]
    q0, qf = check_quality(first), check_quality(final)

    first_terms = _content_words(first)
    retained = (len(first_terms & _content_words(final)) / len(first_terms)
                if first_terms else 1.0)

    a = r["advisory_risk"]
    row.update({
        "content_0": f"{q0['content_passed']}/{q0['content_total']}",
        "content_f": f"{qf['content_passed']}/{qf['content_total']}",
        "improved": qf["content_passed"] > q0["content_passed"],
        "revisions": q["iterations"],
        "retention": round(retained, 2),
        "leak": _instruction_leak(final),
        "len": qf["words"],
        "risk_band": a["band"],
        "text_risk_pp": round(a["text_risk"] * 100, 3),
    })
    return row


# A small, deliberately varied suite: an eligible collaborative project, an
# eligible single-beneficiary ERC, an eligible IA, and one that should be GATED
# (RIA with too few partners) to prove the gate skips drafting.
PROPOSALS = [
    {"id": "P1-crop", "scheme": "RIA",
     "idea": ("A platform using machine learning on low-cost drone imagery to detect "
              "early-stage crop disease in smallholder farms, with an offline mobile app."),
     "ec_contribution": 5_000_000, "total_cost": 6_200_000,
     "consortium_size": 9, "num_countries": 6},
    {"id": "P2-quantum", "scheme": "ERC-STG",
     "idea": ("A theoretical and experimental study of error-corrected qubit control "
              "in silicon spin devices for scalable quantum processors."),
     "ec_contribution": 1_400_000, "total_cost": 1_400_000,
     "consortium_size": 1, "num_countries": 1},
    {"id": "P3-water", "scheme": "IA",
     "idea": ("A low-energy membrane system that recovers clean water and nutrients "
              "from agricultural wastewater for reuse by rural communities."),
     "ec_contribution": 4_000_000, "total_cost": 5_000_000,
     "consortium_size": 6, "num_countries": 5},
    {"id": "P4-gated", "scheme": "RIA",
     "idea": ("A single-lab prototype of a sensor for soil moisture monitoring."),
     "ec_contribution": 600_000, "total_cost": 600_000,
     "consortium_size": 1, "num_countries": 1},
]


def main():
    rows = []
    for p in PROPOSALS:
        print(f"[eval] running {p['id']} ...")
        rows.append(evaluate_one(p))

    print("\n" + "=" * 100)
    print("EVAL SUMMARY")
    print("=" * 100)
    header = (f"{'id':<12}{'scheme':<9}{'elig':<13}{'content':<14}"
              f"{'rev':<5}{'reten':<7}{'leak':<6}{'len':<6}{'risk':<10}")
    print(header)
    print("-" * 100)
    for r in rows:
        if r.get("gated"):
            print(f"{r['id']:<12}{r['scheme']:<9}{r['eligibility']:<13}"
                  f"{'GATED (drafting skipped)':<40}")
            continue
        content = f"{r['content_0']}->{r['content_f']}"
        print(f"{r['id']:<12}{r['scheme']:<9}{r['eligibility']:<13}{content:<14}"
              f"{r['revisions']:<5}{r['retention']:<7}{str(r['leak']):<6}"
              f"{r['len']:<6}{r['risk_band']+' '+str(r['text_risk_pp'])+'pp':<10}")

    drafted = [r for r in rows if not r.get("gated")]
    if drafted:
        n = len(drafted)
        improved = sum(1 for r in drafted if r["improved"])
        leaks = sum(1 for r in drafted if r["leak"])
        avg_ret = sum(r["retention"] for r in drafted) / n
        print("-" * 100)
        print(f"drafted: {n} | loop improved content checks: {improved}/{n} | "
              f"instruction leaks: {leaks}/{n} | avg substance retention: {avg_ret:.2f}")


if __name__ == "__main__":
    main()

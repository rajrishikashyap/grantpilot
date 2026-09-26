"""
The Coordinator (Phase 3C stub).

This is the orchestration layer that ties the four specialists together into a
single proposal assessment. It is the capstone of everything the agents taught
us, and its design encodes two hard-won principles:

  1. Hold the proposal ONCE, as structured fields, and hand those fields to each
     specialist by reference. Nothing is re-typed by a language model, so the
     dropped-budget-zero class of bug cannot happen in the pipeline.

  2. Every JUDGMENT is deterministic. The Coordinator calls the reasoning cores
     directly, check_eligibility, score_budget, score_proposal + explain_proposal,
     and uses a language model ONLY where the job is generation (the Drafting
     section). Routing the budget or eligibility check through an LLM agent would
     put a 3B model back in charge of a number or a verdict, which is exactly the
     failure mode we removed. Reasoning cores are deterministic; the LLM writes.

WHY THIS IS A STUB: in Phase 4 the Coordinator itself becomes a ReAct agent that
decides ordering, retries, and runs the reviewer -> drafting feedback loop (draft,
score the draft's risk, revise, re-score). Here it runs a fixed, honest sequence
so the end-to-end pipeline is provable before that loop is added.

A proposal is a plain dict, for example:
    {
        "id": "DEMO-1",
        "idea": "<one or two sentences describing the research idea>",
        "scheme": "RIA",
        "ec_contribution": 5_000_000,
        "total_cost": 6_200_000,
        "consortium_size": 9,
        "num_countries": 6,
        # optional consortium composition for Model A:
        "num_sme": 3, "num_hes": 3, "num_rec": 2, "num_prc": 1, "num_pub": 0,
    }

Run the demo from the repo root:
    python -m src.agents.coordinator
"""

from src.agents.eligibility_agent import check_eligibility
from src.models.train_model_b import score_budget
from src.models.model_a_infer import score_proposal, explain_proposal
from src.agents.drafting_agent import draft_section


def _risk_band(relative_to_base):
    if relative_to_base < 1.5:
        return "LOW"
    if relative_to_base <= 4.0:
        return "MODERATE"
    return "HIGH"


def assess_proposal(proposal, do_draft=True, verbose=False):
    """
    Run the full assessment pipeline on one structured proposal and return a
    report dict. Each stage reads the fields it needs from `proposal`; none of
    them re-parses free text for its numbers.
    """
    report = {"id": proposal.get("id", "(unnamed)"),
              "scheme": proposal.get("scheme")}

    # --- Stage 1: Eligibility gate (deterministic) ---
    report["eligibility"] = check_eligibility(
        scheme=proposal.get("scheme"),
        ec_contribution=proposal.get("ec_contribution"),
        consortium_size=proposal.get("consortium_size"),
        num_countries=proposal.get("num_countries"),
    )

    # --- Stage 2: Budget anomaly (deterministic, Model B) ---
    report["budget"] = score_budget(
        proposal.get("scheme"),
        proposal.get("ec_contribution"),
    )

    # --- Stage 3: Post-award risk + explanation (deterministic, Model A) ---
    numeric = dict(
        ecMaxContribution=proposal.get("ec_contribution"),
        totalCost=proposal.get("total_cost"),
        consortiumSize=proposal.get("consortium_size"),
        numCountries=proposal.get("num_countries"),
        numSME=proposal.get("num_sme"),
        numHES=proposal.get("num_hes"),
        numREC=proposal.get("num_rec"),
        numPRC=proposal.get("num_prc"),
        numPUB=proposal.get("num_pub"),
    )
    s = score_proposal(proposal.get("idea", ""), proposal.get("scheme"), **numeric)
    e = explain_proposal(proposal.get("idea", ""), proposal.get("scheme"),
                         top_k=5, **numeric)
    report["risk"] = {
        "risk": s["risk"],
        "relative_to_base": s["relative_to_base"],
        "band": _risk_band(s["relative_to_base"]),
        "top_risk_drivers": e["top_risk_drivers"],
        "top_protective_drivers": e["top_protective_drivers"],
    }

    # --- Stage 4: Draft a section (LLM generation, the only non-deterministic step) ---
    if do_draft:
        report["draft"] = draft_section(proposal.get("idea", ""),
                                        proposal.get("scheme"), verbose=verbose)
    else:
        report["draft"] = None

    return report


def _fmt_drivers(drivers):
    return ", ".join(f"{n} ({v:+.2f})" for n, v in drivers) or "none"


def format_report(report):
    """Render the assessment as a readable consolidated report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"PROPOSAL ASSESSMENT: {report['id']}  (scheme {report['scheme']})")
    lines.append("=" * 70)

    # Eligibility
    el = report["eligibility"]
    if not el.get("scheme_known"):
        lines.append("ELIGIBILITY: UNDETERMINED (scheme rules not on file)")
    else:
        lines.append(f"ELIGIBILITY: {el['verdict']}")
        for label, passed, detail in el["checks"]:
            mark = "PASS" if passed is True else "FAIL" if passed is False else "UNCHECKED"
            lines.append(f"    [{mark}] {label} ({detail})")

    # Budget
    b = report["budget"]
    if b.get("scored"):
        flag = "ANOMALOUS" if b["is_anomaly"] else "normal"
        lines.append(f"BUDGET: {flag} (robust z-score {b['robust_z']}, "
                     f"scheme median {b['scheme_median_eur']:,} EUR)")
    else:
        lines.append(f"BUDGET: could not score ({b.get('reason', 'unknown')})")

    # Risk
    r = report["risk"]
    lines.append(f"POST-AWARD RISK: {r['band']} "
                 f"({r['risk']*100:.1f}%, {r['relative_to_base']:.1f}x base rate)")
    lines.append(f"    risk drivers:      {_fmt_drivers(r['top_risk_drivers'])}")
    lines.append(f"    protective drivers: {_fmt_drivers(r['top_protective_drivers'])}")

    # Draft
    lines.append("DRAFT (Concept and Objectives):")
    if report["draft"]:
        for para in report["draft"].split("\n"):
            lines.append("    " + para)
    else:
        lines.append("    (skipped)")

    return "\n".join(lines)


if __name__ == "__main__":
    # End-to-end demo on one proposal. draft=True runs the local LLM once, so
    # this takes a moment on the GTX 1650.
    demo = {
        "id": "DEMO-1",
        "idea": ("A platform using machine learning on low-cost drone imagery to "
                 "detect early-stage crop disease in smallholder farms, with an "
                 "offline mobile app so farmers get advice without reliable internet."),
        "scheme": "RIA",
        "ec_contribution": 5_000_000,
        "total_cost": 6_200_000,
        "consortium_size": 9,
        "num_countries": 6,
        "num_sme": 3, "num_hes": 3, "num_rec": 2, "num_prc": 1, "num_pub": 0,
    }
    report = assess_proposal(demo, do_draft=True, verbose=True)
    print("\n\n" + format_report(report))

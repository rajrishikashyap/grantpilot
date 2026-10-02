"""
The Phase 4 orchestrator (4B).

The deterministic pipeline that runs a proposal end to end. It supersedes the
3C Coordinator stub by adding the quality-driven feedback loop in place of a
single one-shot draft. Design decisions, both already settled:

  - The orchestrator is DETERMINISTIC. The sequence is fixed and known, so a
    3B model is not put in charge of ordering. The LLM only drafts and revises.
  - The proposal is held ONCE as structured fields and handed to each stage by
    reference, so no number or verdict is ever re-transcribed by the model.

Flow:
    1. Eligibility gate (deterministic). If NOT ELIGIBLE, report and STOP:
       there is no point drafting a proposal that cannot be submitted.
    2. Budget anomaly check (deterministic, Model B).
    3. Quality loop (draft, review against quality checks, revise, re-check).
    4. Advisory Model A risk + SHAP on the final draft (reported, not optimised).
    5. One consolidated report.

Run the demo:
    python -m src.agents.pipeline
"""

from src.agents.eligibility_agent import check_eligibility
from src.models.train_model_b import score_budget
from src.agents.quality_loop import improve_draft_quality


def _risk_band(relative_to_base):
    if relative_to_base < 1.5:
        return "LOW"
    if relative_to_base <= 4.0:
        return "MODERATE"
    return "HIGH"


def run_pipeline(proposal, max_iters=2, verbose=True):
    """
    Run the full deterministic assessment pipeline on one structured proposal.
    Returns a report dict. Drafting is skipped when the proposal is NOT
    ELIGIBLE (the gate), and the report says so.
    """
    report = {"id": proposal.get("id", "(unnamed)"),
              "scheme": proposal.get("scheme")}

    # --- Stage 1: Eligibility gate ---
    el = check_eligibility(
        scheme=proposal.get("scheme"),
        ec_contribution=proposal.get("ec_contribution"),
        consortium_size=proposal.get("consortium_size"),
        num_countries=proposal.get("num_countries"),
    )
    report["eligibility"] = el
    verdict = el.get("verdict", "UNDETERMINED")
    if verbose:
        print(f"[pipeline] eligibility: {verdict}")

    # --- Stage 2: Budget anomaly (always runs; cheap and informative) ---
    report["budget"] = score_budget(proposal.get("scheme"),
                                    proposal.get("ec_contribution"))

    # The gate: a NOT ELIGIBLE proposal cannot be submitted, so we do not spend
    # LLM time drafting it. UNDETERMINED still proceeds, with the caveat noted.
    if verdict == "NOT ELIGIBLE":
        report["gated"] = True
        report["quality"] = None
        report["advisory_risk"] = None
        if verbose:
            print("[pipeline] NOT ELIGIBLE, skipping drafting.")
        return report

    # --- Stage 3: Quality loop (drafting + review + revision) ---
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
    if verbose:
        print("[pipeline] running quality loop ...")
    loop = improve_draft_quality(proposal.get("idea", ""), proposal.get("scheme"),
                                 max_iters=max_iters, verbose=verbose, **numeric)
    report["gated"] = False
    report["quality"] = {
        "passed": loop["best_quality"]["passed"],
        "total": loop["best_quality"]["total"],
        "checks": loop["best_quality"]["checks"],
        "first_draft": loop["history"][0][4],   # iteration-0 draft, for the eval
        "final_draft": loop["best_draft"],
        "iterations": len(loop["history"]) - 1,
    }

    # --- Stage 4: Advisory risk (from the loop; reported, not optimised) ---
    a = loop["advisory_risk"]
    a["band"] = _risk_band(a["relative_to_base"])
    report["advisory_risk"] = a

    return report


def _fmt_drivers(drivers):
    return ", ".join(f"{n} ({v:+.2f})" for n, v in drivers) or "none"


def format_report(report):
    lines = []
    lines.append("=" * 70)
    lines.append(f"PROPOSAL ASSESSMENT: {report['id']}  (scheme {report['scheme']})")
    lines.append("=" * 70)

    el = report["eligibility"]
    lines.append(f"ELIGIBILITY: {el.get('verdict', 'UNDETERMINED')}")
    for label, passed, detail in el.get("checks", []):
        mark = "PASS" if passed is True else "FAIL" if passed is False else "UNCHECKED"
        lines.append(f"    [{mark}] {label} ({detail})")

    b = report["budget"]
    if b.get("scored"):
        flag = "ANOMALOUS" if b["is_anomaly"] else "normal"
        lines.append(f"BUDGET: {flag} (robust z-score {b['robust_z']}, "
                     f"scheme median {b['scheme_median_eur']:,} EUR)")
    else:
        lines.append(f"BUDGET: could not score ({b.get('reason', 'unknown')})")

    if report["gated"]:
        lines.append("DRAFT: skipped (proposal is NOT ELIGIBLE).")
        return "\n".join(lines)

    q = report["quality"]
    lines.append(f"QUALITY: {q['passed']}/{q['total']} checks passed "
                 f"after {q['iterations']} revision(s)")
    for label, passed, detail in q["checks"]:
        lines.append(f"    [{'PASS' if passed else 'GAP '}] {label} ({detail})")

    a = report["advisory_risk"]
    lines.append(f"ADVISORY RISK: {a['band']} "
                 f"({a['risk']*100:.2f}%, {a['relative_to_base']:.2f}x base); "
                 f"marginal text risk {a['text_risk']*100:.3f} pp")
    lines.append(f"    risk words: {[w for w, _ in a['risk_words']]}")

    lines.append("FINAL DRAFT (Concept and Objectives):")
    for para in q["final_draft"].split("\n"):
        lines.append("    " + para)

    return "\n".join(lines)


if __name__ == "__main__":
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
    report = run_pipeline(demo, max_iters=2, verbose=True)
    print("\n\n" + format_report(report))

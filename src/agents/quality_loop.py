"""
The quality-driven reviewer-to-drafting feedback loop (Phase 4, 4B).

Background: the 4A risk-minimising loop was a confirmed dead end. A RAG-grounded
first draft is already net-protective on Model A's risk, so minimising "risk
words" only strips the on-topic content that was protective. Conclusion: the
loop's job is not risk-reduction, it is QUALITY.

This loop drives on deterministic quality checks a human reviewer would actually
make, not on the risk model:

    1. Draft the section (Drafting agent, RAG-grounded).
    2. check_quality(): does it have a concept paragraph, three-plus specific
       numbered objectives, a methodology/validation mention, an
       impact/dissemination mention, and a sensible length?
    3. If gaps remain, ask a reviser to fix exactly those gaps (preserving the
       existing content), then re-check.
    4. Keep the draft that passes the most checks. Stop when all pass or at
       max_iters.

Model A's risk and SHAP drivers are computed once on the final draft and
attached as ADVISORY context. They are reported, never optimised against, which
is the honest use after 4A showed optimising them is counterproductive.
"""

import re

from src.agents.drafting_agent import draft_section, _strip_dashes
from src.agents.llm import call_llm
from src.models.model_a_infer import score_proposal, text_risk


# Keyword sets for the two content checks. Substrings, so "disseminate",
# "dissemination" and "beneficiaries" all match their stems.
METHODOLOGY_KW = ["validat", "trial", "evaluat", "benchmark", "method",
                  "pilot", "experiment", "measure", "metric", "test"]
IMPACT_KW = ["impact", "disseminat", "stakeholder", "adoption", "exploit",
             "uptake", "scal", "policy", "beneficiar", "market"]


def _numbered_lines(text):
    """Lines that look like a numbered objective: '1. ...' or '1) ...'."""
    return [ln.strip() for ln in text.splitlines()
            if re.match(r"^\s*\d+[.)]\s+", ln)]


def _word_count(s):
    return len(re.findall(r"\w+", s))


def check_quality(draft, min_objectives=3, min_obj_words=8,
                  min_words=130, max_words=350):
    """
    Run the deterministic quality checks. Returns a dict with each check's
    (label, passed, detail), the count passed, and the list of gap labels the
    reviser should fix. No LLM here; this is the objective part the loop trusts.
    """
    text = (draft or "").strip()
    total_words = _word_count(text)

    objectives = _numbered_lines(text)
    specific = [o for o in objectives if _word_count(o) >= min_obj_words]

    # Concept = the prose before the first numbered objective.
    first = re.search(r"\n\s*\d+[.)]\s+", "\n" + text)
    concept = text[:first.start()] if first else text
    concept_words = _word_count(concept)

    low = text.lower()
    has_method = any(k in low for k in METHODOLOGY_KW)
    has_impact = any(k in low for k in IMPACT_KW)

    checks = [
        ("has a concept paragraph", concept_words >= 25,
         f"{concept_words} words before the objectives"),
        (f"has at least {min_objectives} numbered objectives",
         len(objectives) >= min_objectives, f"found {len(objectives)}"),
        (f"objectives are specific (>= {min_obj_words} words each)",
         len(specific) >= min_objectives,
         f"{len(specific)} of {len(objectives)} are specific"),
        ("mentions methodology or validation", has_method,
         "present" if has_method else "absent"),
        ("mentions impact or dissemination", has_impact,
         "present" if has_impact else "absent"),
        (f"length between {min_words} and {max_words} words",
         min_words <= total_words <= max_words, f"{total_words} words"),
    ]
    gaps = [label for label, passed, _ in checks if not passed]
    passed = sum(1 for _, p, _ in checks if p)
    # The length check (always last) is a FORM check. The rest are CONTENT
    # checks, which the loop prioritises: a draft that gained impact but ran a
    # little long is better than one still missing impact. Content-first.
    content_checks = checks[:-1]
    content_passed = sum(1 for _, p, _ in content_checks if p)
    return {"checks": checks, "passed": passed, "total": len(checks),
            "content_passed": content_passed, "content_total": len(content_checks),
            "gaps": gaps, "words": total_words, "n_objectives": len(objectives)}


def _revise_for_quality(idea, scheme, draft, gaps):
    """One revision pass that targets the specific quality gaps found."""
    gap_text = "; ".join(gaps)
    prompt = (
        "You are improving the Concept and Objectives section of an EU research "
        "proposal. A reviewer found these specific gaps you must fix: "
        f"{gap_text}.\n\n"
        "Rewrite the section to fix those gaps while fully preserving the "
        "existing concept and the real subject matter. The result must have a "
        "concept paragraph and at least three specific numbered objectives, and "
        "it must address methodology or validation and impact or dissemination "
        "WOVEN INTO the concept paragraph and the objectives. "
        "Do NOT add labelled sections such as 'Methodology:' or 'Impact:'. "
        "Do NOT copy or restate these instructions anywhere; every numbered "
        "objective must be a real project objective, not a note about what to "
        "include. Be concise: about 210 words, never exceed 250 words. Plain "
        "formal English, no em dashes. Output only the revised section.\n\n"
        f"Research idea: {idea}\n"
        f"Funding scheme: {scheme}\n\n"
        f"Current draft:\n{draft}\n\n"
        "Revised section:"
    )
    raw = call_llm(prompt, temperature=0.3)
    return _strip_dashes(raw.strip())


def _dedupe_section_headers(text):
    """Keep only the first 'Concept:' and first 'Objectives:' header line; a 3B
    reviser sometimes repeats them, which looks sloppy in the UI. Removing the
    duplicate header leaves the numbered objectives contiguous."""
    seen = set()
    out = []
    for line in (text or "").splitlines():
        key = line.strip().rstrip(":").lower()
        if key in ("concept", "objectives"):
            if key in seen:
                continue
            seen.add(key)
        out.append(line)
    return "\n".join(out)


def improve_draft_quality(idea, scheme, max_iters=2, verbose=True, **numeric):
    """
    Draft and iteratively revise toward passing all quality checks. Model A risk
    and SHAP drivers are attached as advisory context on the final draft.

    Returns:
      best_draft     - draft passing the most checks (section headers de-duped)
      best_quality   - its check_quality() result
      history        - [(iteration, passed, total, gaps, draft), ...]
      advisory_risk  - {risk, relative_to_base, text_risk, risk_words} (not optimised)
    """
    if verbose:
        print("### Quality loop: initial draft (RAG-grounded) ###")
    draft = draft_section(idea, scheme, verbose=False)
    q = check_quality(draft)
    history = [(0, q["passed"], q["total"], q["gaps"], draft)]
    # Selection key: content checks first, then total checks. So a draft that
    # gained a content check always beats one that only kept a form check.
    best_key, best_draft, best_q = (q["content_passed"], q["passed"]), draft, q
    if verbose:
        print(f"iteration 0: {q['content_passed']}/{q['content_total']} content "
              f"({q['passed']}/{q['total']} total), gaps: {q['gaps']}")

    for i in range(1, max_iters + 1):
        # Stop once every CONTENT check passes. Length is soft; chasing it
        # further just makes the reviser oscillate.
        if q["content_passed"] == q["content_total"]:
            if verbose:
                print("all content checks pass, stopping.")
            break
        if verbose:
            print(f"\n### Revision {i}: fixing {q['gaps']} ###")
        draft = _revise_for_quality(idea, scheme, draft, q["gaps"])
        q = check_quality(draft)
        history.append((i, q["passed"], q["total"], q["gaps"], draft))
        if verbose:
            print(f"iteration {i}: {q['content_passed']}/{q['content_total']} content "
                  f"({q['passed']}/{q['total']} total), gaps: {q['gaps']}")
        key = (q["content_passed"], q["passed"])
        if key > best_key:
            best_key, best_draft, best_q = key, draft, q

    # Clean up any duplicated 'Concept:' / 'Objectives:' headers the 3B reviser
    # may have left, then re-check so the reported quality matches the final text.
    best_draft = _dedupe_section_headers(best_draft)
    best_q = check_quality(best_draft)

    # Advisory risk on the chosen draft. Reported, not optimised.
    s = score_proposal(best_draft, scheme, **numeric)
    tr = text_risk(best_draft, scheme, top_k=6, **numeric)
    advisory = {
        "risk": s["risk"],
        "relative_to_base": s["relative_to_base"],
        "text_risk": tr["text_risk"],
        "risk_words": tr["risk_words"],
    }
    return {"best_draft": best_draft, "best_quality": best_q,
            "history": history, "advisory_risk": advisory}
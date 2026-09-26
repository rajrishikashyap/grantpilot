"""
The reviewer-to-drafting feedback loop (Phase 4 core).

The loop, deterministic control flow around two LLM generation steps:

    1. Draft the section (Drafting agent, RAG-grounded).
    2. Score its TEXT-ONLY risk with Model A + SHAP (text_risk). Scheme and
       numeric features are held fixed, so this number moves only with the
       wording.
    3. Take the top risk-raising words and ask a reviser to reframe them while
       preserving meaning.
    4. Re-score. Keep the lowest-text-risk version. Repeat up to max_iters.

WHY ONLY THE TEXT RISK: Model A's overall risk is dominated by the funding
scheme, which the draft cannot change. The text contribution is the only part
the wording controls, so it is the honest target for a text-revision loop.

A CAUTION THIS LOOP MAKES VISIBLE: words correlated with termination risk are
often the proposal's core topic (for a crop-disease proposal, "disease" may be
a top risk word). Minimising them can strip substance. The loop does not judge
that; the eval does. This is a demonstration of optimising against a
correlational model, and its limits, not a claim that lower text-risk is better.
"""

from src.models.model_a_infer import text_risk
from src.agents.drafting_agent import draft_section, _strip_dashes
from src.agents.llm import call_llm


def _revise(idea, scheme, previous_draft, risk_words):
    """One revision pass. Pure generation (no tools, no RAG), so a direct LLM
    call rather than a ReAct loop. Returns the revised, dash-cleaned section."""
    words = ", ".join(w for w, _ in risk_words)
    prompt = (
        "You are revising the Concept and Objectives section of an EU research "
        "proposal. A risk model flags the following terms in the current draft as "
        f"statistically associated with higher project-termination risk: {words}.\n\n"
        "Rewrite the section to reduce reliance on those specific terms while "
        "fully preserving the technical meaning, the concept, and the numbered "
        "objectives. Do not drop essential subject matter; reframe rather than "
        "delete. Keep it between 150 and 250 words and NO LONGER than the current "
        "draft, plain formal English, no em dashes. Output only the revised "
        "section, nothing else.\n\n"
        f"Research idea: {idea}\n"
        f"Funding scheme: {scheme}\n\n"
        f"Current draft:\n{previous_draft}\n\n"
        "Revised section:"
    )
    # A little temperature so the rewrite actually differs from the original.
    raw = call_llm(prompt, temperature=0.3)
    return _strip_dashes(raw.strip())


def improve_draft(idea, scheme, max_iters=2, top_words=6, verbose=True, **numeric):
    """
    Produce a draft and iteratively revise it to lower its text-only risk.

    Returns a dict:
      best_draft      - the lowest-text-risk version seen
      best_text_risk  - its text-risk score
      history         - list of (iteration, text_risk, draft), iteration 0 = first draft
    """
    if verbose:
        print("### Feedback loop: initial draft (RAG-grounded) ###")
    draft = draft_section(idea, scheme, verbose=False)
    tr = text_risk(draft, scheme, top_k=top_words, **numeric)
    history = [(0, tr["text_risk"], draft)]
    best_draft, best_score = draft, tr["text_risk"]
    if verbose:
        print(f"iteration 0: marginal text risk = {tr['text_risk']*100:.3f} pp "
              f"(draft risk {tr['risk_text']*100:.2f}%)")

    for i in range(1, max_iters + 1):
        risk_words = text_risk(draft, scheme, top_k=top_words, **numeric)["risk_words"]
        if not risk_words:
            if verbose:
                print("no positive risk words left, stopping.")
            break
        if verbose:
            print(f"\n### Revision {i}: reframing "
                  f"{[w for w, _ in risk_words]} ###")
        draft = _revise(idea, scheme, draft, risk_words)
        tr_i = text_risk(draft, scheme, top_k=top_words, **numeric)
        score = tr_i["text_risk"]
        history.append((i, score, draft))
        if verbose:
            print(f"iteration {i}: marginal text risk = {score*100:.3f} pp "
                  f"(draft risk {tr_i['risk_text']*100:.2f}%)")
        if score < best_score:
            best_draft, best_score = draft, score

    return {"best_draft": best_draft, "best_text_risk": best_score, "history": history}

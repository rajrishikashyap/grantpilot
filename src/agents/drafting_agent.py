"""
The Drafting agent: writes a grounded proposal section using the RAG layer.

Unlike Budget and Reviewer (which wrap a model that returns a fixed result and
have the LLM only narrate it), Drafting is GENERATIVE: the LLM writes the
proposal text. The job of the RAG tool here is grounding. Before writing, the
agent retrieves real funded projects in the same area with search_grants, so
the draft is shaped by how successful proposals in this field are actually
framed, instead of the model free-associating from its training.

This is retrieval-augmented generation inside the same ReAct loop: retrieve
first (Action), then generate (Final Answer). No new engine machinery.

House rule: the GrantPilot project uses no em dashes anywhere. A 3B model will
emit them anyway, so we strip them from the generated draft deterministically
rather than trusting the prompt to hold.
"""

from src.rag.search import make_rag_tool
from src.agents.base import Agent
from src.agents.react import run_agent


DRAFTING_ROLE = (
    "You are a grant proposal writer for EU research funding. Given a research "
    "idea and its funding scheme, you draft the Concept and Objectives section "
    "of a proposal. "
    "First call search_grants once to retrieve three to five real funded projects "
    "in the same area, so your draft is grounded in how successful proposals in "
    "this field are framed. "
    "Then write the section as your Final Answer. Use the retrieved projects for "
    "structure, framing and vocabulary, but the draft must be original to the "
    "given idea and must not copy any retrieved sentence. "
    "To prove the draft is grounded in the retrieved evidence, the opening "
    "paragraph must position this idea against how existing EU-funded work in the "
    "same area approaches the problem, and must name at least two concrete "
    "techniques, methods or data sources that actually appear in the retrieved "
    "objectives (for example the sensing methods, data types or model approaches "
    "those projects use). Refer to approaches and techniques only; never invent "
    "project names or acronyms. "
    "The Final Answer must be the drafted section only: one opening paragraph "
    "stating the concept, why it matters, and how it relates to existing funded "
    "approaches, then three or four numbered objectives specific to this idea. "
    "Keep it between 150 and 250 words. Write in plain formal English and do not "
    "use em dashes."
)


# The no-em-dash house rule, enforced on output rather than trusted to the model.
_EMDASH = "—"   # em dash
_ENDASH = "–"   # en dash


def _strip_dashes(text):
    if not text:
        return text
    text = text.replace(" " + _EMDASH + " ", ", ")
    text = text.replace(_EMDASH, ", ")
    text = text.replace(" " + _ENDASH + " ", ", ")
    text = text.replace(_ENDASH, "-")
    return text


def make_drafting_agent():
    """Build the Drafting agent: the drafting role plus the RAG search tool."""
    rag_tool = make_rag_tool()
    return Agent(
        name="DraftingAgent",
        role=DRAFTING_ROLE,
        registry={rag_tool.name: rag_tool},
        max_steps=4,
    )


def draft_section(idea, scheme, verbose=True):
    """
    Convenience entry point: draft a Concept and Objectives section for a
    research idea under a funding scheme, with the house-style dash rule applied
    to the result. Returns the cleaned draft string.
    """
    task = (
        f"Draft the Concept and Objectives section for a proposal under the "
        f"{scheme} scheme. Research idea: {idea}"
    )
    agent = make_drafting_agent()
    raw = agent.run(task, verbose=verbose)
    return _strip_dashes(raw)

"""
3B test: prove semantic search works, then prove an AGENT can use it.

Two stages, run in order:

STAGE 1 (no LLM): fire a few queries straight at search_grants and eyeball
the hits. This is the inspect-do-not-trust step. You are checking that a
query about, say, batteries actually returns battery projects and not random
ones. If stage 1 looks wrong, the index is wrong, and no agent will fix that.

STAGE 2 (LLM + tool): register the RAG search as a tool in the SAME ReAct
engine from 3A and give the agent a question it can only answer by searching.
If the agent calls search_grants and answers from the results, retrieval is
now a capability the agents in 3C can rely on. The engine code is untouched:
we only changed what is in the tool registry. That is the whole point of 3B.

Run from the repo root:
    python -m src.rag.test_rag
"""

from src.rag.search import search_grants, make_rag_tool
from src.agents.react import run_agent


def stage1_direct_search():
    print("#" * 70)
    print("# STAGE 1: direct semantic search (no LLM)")
    print("#" * 70)
    queries = [
        "artificial intelligence for medical diagnosis",
        "carbon capture and storage technology",
        "quantum computing hardware",
    ]
    for q in queries:
        print("\n" + "=" * 70)
        print(search_grants(q, k=3))


def stage2_agent_uses_rag():
    print("\n" + "#" * 70)
    print("# STAGE 2: the ReAct agent uses search_grants as a tool")
    print("#" * 70)

    # Build a registry with just the RAG tool. The engine treats it exactly
    # like the toy tools in 3A: it appears in the prompt, the model can choose
    # it, our code runs it and feeds the result back as an Observation.
    rag_tool = make_rag_tool()
    registry = {rag_tool.name: rag_tool}

    # A question the model cannot answer from training: it does not know what
    # is in OUR index. It must search to answer well.
    question = (
        "Find three examples of EU-funded projects about hydrogen fuel cells, "
        "and briefly say what they focus on. Use the search tool."
    )

    answer = run_agent(question, registry, max_steps=6, verbose=True)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)


if __name__ == "__main__":
    stage1_direct_search()
    stage2_agent_uses_rag()

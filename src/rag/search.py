"""
Search the grant index, and expose that search as a ReAct tool.

Two jobs:
  1. search_grants(query, k) : embed the query with the SAME model used to
     build the index, ask Chroma for the k nearest objectives, return them as
     a readable string.
  2. make_rag_tool() : wrap search_grants in a Tool object so it drops
     straight into the ReAct registry from 3A. This is the bridge. The engine
     does not change at all; retrieval is just another tool the agent can pick.

The model and collection are loaded once and cached in module globals, so an
agent that calls the tool several times in one run does not reload the model
each time (that reload is seconds of wasted work on a 3B-class machine).
"""

from sentence_transformers import SentenceTransformer
import chromadb

# Must match build_index.py exactly, or queries land in a different space
# from the documents and every result is noise.
CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "grants"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Cached singletons. Loaded lazily on first search, reused after.
_model = None
_collection = None


def _load():
    """Load the model and open the collection once, then cache them."""
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        # get_collection (not create) because build_index.py already made it.
        # If it is missing, the error tells the user to run the builder first.
        try:
            _collection = client.get_collection(COLLECTION_NAME)
        except Exception:
            raise SystemExit(
                f"No Chroma collection '{COLLECTION_NAME}' at {CHROMA_PATH}. "
                "Run:  python -m src.rag.build_index   first."
            )
    return _model, _collection


def search_grants(query, k=5):
    """
    Return the k most semantically similar grant objectives to `query`,
    formatted as a plain-text block the LLM (or a human) can read.

    Similarity is 1 - cosine_distance, so 1.0 is identical meaning and 0.0 is
    unrelated. We show it so the agent can judge whether a hit is actually
    relevant or just the closest of a bad bunch.
    """
    model, collection = _load()

    q_vec = model.encode([query], normalize_embeddings=True)
    res = collection.query(query_embeddings=q_vec.tolist(), n_results=k)

    # Chroma returns each field as a list-of-lists (one inner list per query).
    # We sent one query, so we read index [0].
    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    if not ids:
        return f"No grants found for query: {query!r}"

    lines = [f"Top {len(ids)} grants matching: {query!r}\n"]
    for i in range(len(ids)):
        meta = metas[i]
        sim = 1 - dists[i]
        objective = docs[i].strip().replace("\n", " ")
        # Trim the objective so one hit does not flood the prompt. The agent
        # gets the gist; it can reason about the topic without the full text.
        snippet = objective[:300] + ("..." if len(objective) > 300 else "")
        lines.append(
            f"[{i+1}] similarity {sim:.3f} | scheme: {meta.get('fundingScheme','')} "
            f"| status: {meta.get('status','')}\n"
            f"    {meta.get('acronym','')}: {meta.get('title','')}\n"
            f"    Objective: {snippet}\n"
        )
    return "\n".join(lines)


def make_rag_tool():
    """
    Build a Tool that the ReAct engine can register. Importing Tool here (not
    at module top) keeps a plain `import search` from dragging in the agents
    package when all you want is search_grants.

    The tool's func takes the standard args dict the parser produces, reads
    'query' and optional 'k', and returns the formatted search string.
    """
    from src.agents.tools import Tool

    def _run(args):
        query = args.get("query", "").strip()
        if not query:
            return "Error: search_grants needs a 'query' string."
        k = args.get("k", 5)
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = 5
        return search_grants(query, k=k)

    return Tool(
        name="search_grants",
        description=(
            "Search a database of 35,000 real EU-funded research grants by "
            "meaning, not keywords. Use it to find precedent projects, see how "
            "similar work was funded, or check what already exists in a field. "
            'Action Input must be JSON like {"query": "solar hydrogen storage", "k": 5}. '
            "k is optional and defaults to 5."
        ),
        func=_run,
    )


if __name__ == "__main__":
    # Direct check, no agent involved: run a few queries and print the hits.
    # Run: python -m src.rag.search
    for q in [
        "machine learning for early cancer detection",
        "offshore wind turbine maintenance robots",
        "preserving endangered languages with technology",
    ]:
        print("=" * 70)
        print(search_grants(q, k=3))

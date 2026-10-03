"""
Structured RAG search for the API.

search_grants() (in search.py) returns a formatted text block, which is right
for the agent's ReAct observation but wrong for a web UI. This returns the same
hits as a list of plain dicts the frontend can render as cards. It reuses the
cached model and Chroma collection from search.py, so there is still one loader.
"""

import src.rag.search as S


def search_records(query, k=5):
    """Return the top-k grant hits as a list of dicts (not a text block)."""
    S._load()  # populates S._model and S._collection (cached)
    model, collection = S._model, S._collection

    q_vec = model.encode([query], normalize_embeddings=True)
    res = collection.query(query_embeddings=q_vec.tolist(), n_results=k)

    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    out = []
    for i in range(len(ids)):
        m = metas[i] or {}
        objective = (docs[i] or "").strip().replace("\n", " ")
        out.append({
            "id": ids[i],
            "acronym": m.get("acronym", ""),
            "title": m.get("title", ""),
            "scheme": m.get("fundingScheme", ""),
            "status": m.get("status", ""),
            "similarity": round(1 - dists[i], 3),
            "objective": objective[:280] + ("\u2026" if len(objective) > 280 else ""),
        })
    return out
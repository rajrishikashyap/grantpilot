"""
Build the vector index over CORDIS project objectives.

This script runs ONCE (and again only if you want to rebuild). It reads
project.csv, turns each project's objective text into an embedding with a
local sentence-transformers model, and stores those vectors in a persistent
ChromaDB collection on disk. After this runs, search is instant: we never
re-embed the 35k objectives again, we only embed the incoming query.

Why this shape:
  - Embedding 35k docs is the slow part, so we do it here, offline, once.
  - ChromaDB persists to disk (data/chroma), so the index survives restarts.
  - We compute embeddings ourselves with SentenceTransformer rather than
    handing Chroma an embedding_function, because the SAME model must embed
    both the documents (here) and the queries (in search.py). Owning the
    model in our own code makes that guarantee obvious and reusable.

Run from the repo root:
    python -m src.rag.build_index            # full build, all rows
    python -m src.rag.build_index 500        # quick test build, first 500

Install once (in the grantpilot env):
    pip install chromadb sentence-transformers pandas
"""

import sys
import time
from sentence_transformers import SentenceTransformer
import chromadb

# The project's ONE canonical CSV reader. Reusing it (instead of re-reading
# project.csv here) is the whole fix: the RAG corpus is now parsed exactly
# like the data Models A and B were built on, so the two can never drift.
from src.data.load import load_projects as _load_canonical

# ---------------------------------------------------------------------------
# Configuration. One place to change paths and names.
# ---------------------------------------------------------------------------
CSV_PATH = "data/raw/project.csv"       # the CORDIS H2020 projects file
CHROMA_PATH = "data/chroma"             # where the vector store lives on disk
COLLECTION_NAME = "grants"              # the named collection inside Chroma
EMBED_MODEL = "all-MiniLM-L6-v2"        # 384-dim, small, fast, runs local

# The columns we actually need. We read them as strings so the European
# decimal format in money columns is irrelevant (we are not touching money
# here). If any of these names is wrong for your file, the script prints the
# real column list and stops, so you can correct it.
TEXT_COL = "objective"                  # the text we embed and search over
ID_COL = "id"                           # unique id per project (CORDIS calls it 'id')
META_COLS = ["acronym", "title", "fundingScheme", "status"]  # shown with hits


def load_projects(limit=None):
    """
    Get the projects through the canonical loader, then keep only what we
    index. We do NOT re-parse the CSV here. The earlier version did, with a
    different parser, and that is exactly how 1,255 fragmented rows leaked
    into the index: two readers, two answers. One reader, one answer.
    """
    df = _load_canonical()

    wanted = [ID_COL, TEXT_COL] + META_COLS
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        raise SystemExit(
            f"load_projects() did not return columns {missing}. "
            f"Available columns:\n{list(df.columns)}"
        )
    df = df[wanted].copy()

    # Drop rows with no objective text (nothing to embed). The canonical
    # loader keeps empty-objective rows and flags them; we drop them here
    # because a vector of an empty string is meaningless.
    before = len(df)
    df = df[df[TEXT_COL].astype(str).str.strip() != ""]
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped} rows with empty objective text.")

    # Chroma metadata values cannot be None. The canonical loader already
    # uses "" for blanks, but guard anyway so add() never chokes on a NaN.
    for col in META_COLS:
        df[col] = df[col].fillna("")

    if limit is not None:
        df = df.head(limit)

    return df.reset_index(drop=True)


def build(limit=None):
    t0 = time.time()

    print(f"Loading projects from {CSV_PATH} ...")
    df = load_projects(limit=limit)
    print(f"Loaded {len(df)} projects to index.")

    # Load the embedding model. sentence-transformers auto-selects the GPU if
    # a CUDA build of torch is installed, else CPU. Either works for MiniLM.
    print(f"Loading embedding model '{EMBED_MODEL}' (first run downloads it) ...")
    model = SentenceTransformer(EMBED_MODEL)
    device = model.device
    print(f"Embedding on device: {device}")

    # NOTE ON TRUNCATION: MiniLM's max input is 256 tokens (~1000 chars).
    # Objectives are capped near 2000 chars, so long ones get truncated to
    # their first part. That is fine for a first retrieval build (the opening
    # of a grant objective carries most of the topic signal), and it is a
    # documented limitation, not a silent one. Chunking longer objectives is
    # a later improvement if retrieval quality demands it.

    texts = df[TEXT_COL].tolist()
    ids = df[ID_COL].tolist()

    print("Embedding objectives (this is the slow step) ...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # unit vectors, so cosine = dot product
    )
    print(f"Produced {embeddings.shape[0]} vectors of dim {embeddings.shape[1]}.")

    # Open (or create) the persistent Chroma store and collection. We set the
    # distance metric to cosine because our embeddings are normalized and
    # cosine similarity is the standard for sentence embeddings.
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # If the collection already exists from a previous run, drop it so a
    # rebuild is clean rather than appending duplicates.
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' exists, deleting for clean rebuild.")
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Build the metadata records shown alongside each search hit.
    metadatas = []
    for _, row in df.iterrows():
        metadatas.append({col: row[col] for col in META_COLS})

    # Add in chunks so we never hand Chroma one giant call. 5000 is a safe
    # batch size well under Chroma's per-call limits.
    print("Writing vectors to ChromaDB ...")
    CHUNK = 5000
    for start in range(0, len(ids), CHUNK):
        end = start + CHUNK
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end].tolist(),
            documents=texts[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"  wrote {min(end, len(ids))}/{len(ids)}")

    count = collection.count()
    elapsed = time.time() - t0
    print(f"\nDone. Collection '{COLLECTION_NAME}' now holds {count} projects.")
    print(f"Stored at: {CHROMA_PATH}")
    print(f"Total time: {elapsed:.1f}s")

    # Immediate sanity query so you see retrieval working before you leave.
    print("\nSanity query: 'renewable energy storage for coastal regions'")
    q = model.encode(
        ["renewable energy storage for coastal regions"],
        normalize_embeddings=True,
    )
    res = collection.query(query_embeddings=q.tolist(), n_results=3)
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        dist = res["distances"][0][i]
        print(f"  [{i+1}] ({1 - dist:.3f}) {meta.get('acronym','')}: "
              f"{meta.get('title','')[:80]}")


if __name__ == "__main__":
    # Optional first argument = row limit for a quick test build.
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    build(limit=lim)

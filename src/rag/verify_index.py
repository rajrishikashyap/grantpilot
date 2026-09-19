"""
verify_index.py (v3) - audit the RAG index against the CANONICAL loader.

The reference set is now src/data/load.py's load_projects(), the exact same
reader the models use. So this checks the one thing that matters: does the
index hold precisely the projects the rest of the project agrees exist.

Run from the repo root:
    python -m src.rag.verify_index
"""

import chromadb

from src.data.load import load_projects
from src.rag.build_index import CHROMA_PATH, COLLECTION_NAME, ID_COL, TEXT_COL


def main():
    print("Loading canonical project set (src/data/load.py) ...")
    df = load_projects()
    print(f"Canonical rows: {len(df)}")

    ids = df[ID_COL].astype(str)
    print(f"Unique ids: {ids.nunique()} | duplicated: {int(ids.duplicated().sum())}")

    has_obj = df[TEXT_COL].astype(str).str.strip() != ""
    clean_obj_ids = set(ids[has_obj])
    print(f"Canonical rows with objective text (what should be indexed): {len(clean_obj_ids)}")

    print("\nStatus breakdown (canonical):")
    print(df["status"].value_counts(dropna=False).to_string())

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection(COLLECTION_NAME)
    idx_ids = set(col.get(include=[])["ids"])
    print(f"\nChroma collection count: {len(idx_ids)}")

    wrong = idx_ids - clean_obj_ids     # in index, not a real objective row
    missing = clean_obj_ids - idx_ids   # real row, not in index
    print(f"\nWRONG   (indexed but not a canonical objective row): {len(wrong)}")
    print(f"MISSING (canonical objective row not indexed):        {len(missing)}")
    if wrong:
        print(f"    example wrong ids: {list(wrong)[:10]}")
    if missing:
        print(f"    example missing ids: {list(missing)[:10]}")

    print("\nVerdict:")
    if not wrong and not missing:
        print("  CLEAN. The index is exactly the canonical objective-bearing set.")
    else:
        print("  NOT CLEAN. Rebuild with the corrected build_index.py, then re-run this.")


if __name__ == "__main__":
    main()

"""Export minimal text+label data for the Colab transformer.
Only objective text and label, keeps the upload small."""
import pandas as pd
from pathlib import Path

CLEAN = Path("data/clean")
OUT = Path("data/clean")

for split in ["train", "test"]:
    df = pd.read_parquet(CLEAN / f"model_a_{split}.parquet")
    slim = df[["id", "objective", "label"]].copy()
    out = OUT / f"model_a_{split}_text.csv"
    slim.to_csv(out, index=False)
    print(f"{split}: {len(slim):,} rows -> {out} "
          f"({out.stat().st_size/1e6:.1f} MB, {slim['label'].mean()*100:.1f}% failures)")
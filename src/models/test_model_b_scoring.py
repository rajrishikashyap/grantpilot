"""Sanity-test Model B's single-budget scorer with realistic cases."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from train_model_b import score_budget

cases = [
    ("MSCA-IF", 187_000),      # normal MSCA-IF
    ("MSCA-IF", 2_000_000),    # absurdly large MSCA-IF -> anomaly
    ("RIA", 5_000_000),        # normal RIA
    ("RIA", 150_000),          # tiny RIA -> anomaly
    ("MSCA-ITN", 255_000),     # the flagged low ITN from training
]
for scheme, budget in cases:
    r = score_budget(scheme, budget)
    flag = "ANOMALY" if r.get("is_anomaly") else "ok" if r.get("scored") else "n/a"
    print(f"[{flag:7s}] {r.get('explanation', r.get('reason'))}")
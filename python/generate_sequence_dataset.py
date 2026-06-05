from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from brake_world_model.physics import generate_synthetic_sequence_dataset


def parse_args():
    parser = argparse.ArgumentParser(description="Generate trajectory CSV for LSTM/GRU world-model training.")
    parser.add_argument("--out", type=Path, default=Path("data/brake_sequence_dataset.csv"))
    parser.add_argument("--trajectories", type=int, default=800)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=19)
    return parser.parse_args()


def main():
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_synthetic_sequence_dataset(args.trajectories, args.steps, args.seed)
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"saved {len(df)} rows: {args.out}")


if __name__ == "__main__":
    main()


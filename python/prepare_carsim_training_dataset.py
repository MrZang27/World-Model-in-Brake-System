from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare CarSim trajectories for braking world-model training."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/carsim_brake_sequence_dataset.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/carsim_brake_sequence_training.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/carsim_training_dataset_summary.json"),
    )
    parser.add_argument("--stop-speed-mps", type=float, default=0.05)
    return parser.parse_args()


def clean_trajectory(group: pd.DataFrame, stop_speed_mps: float) -> pd.DataFrame:
    trajectory = group.sort_values("step").copy()
    trajectory["v_mps"] = trajectory["v_mps"].clip(lower=0.0)
    trajectory["v_next_mps"] = trajectory["v_next_mps"].clip(lower=0.0)

    stopped_now = trajectory["v_mps"] <= stop_speed_mps
    stopped_next = trajectory["v_next_mps"] <= stop_speed_mps
    trajectory.loc[stopped_now, "a_mps2"] = 0.0
    trajectory.loc[stopped_next, "a_next_mps2"] = 0.0

    stop_indices = np.flatnonzero(stopped_next.to_numpy())
    if len(stop_indices):
        trajectory = trajectory.iloc[: stop_indices[0] + 1].copy()

    trajectory["step"] = np.arange(len(trajectory), dtype=int)
    return trajectory


def main():
    args = parse_args()
    data = pd.read_csv(args.input)
    required = {
        "trajectory_id",
        "step",
        "v_mps",
        "a_mps2",
        "v_next_mps",
        "a_next_mps2",
    }
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    original_rows = len(data)
    cleaned = pd.concat(
        [
            clean_trajectory(group, args.stop_speed_mps)
            for _, group in data.groupby("trajectory_id", sort=False)
        ],
        ignore_index=True,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(args.output, index=False)

    lengths = cleaned.groupby("trajectory_id").size()
    summary = {
        "input": str(args.input),
        "output": str(args.output),
        "stop_speed_mps": args.stop_speed_mps,
        "original_rows": original_rows,
        "cleaned_rows": len(cleaned),
        "removed_rows": original_rows - len(cleaned),
        "trajectory_count": int(cleaned["trajectory_id"].nunique()),
        "physical_condition_count": int(
            cleaned[["initial_speed_kph", "mu"]].drop_duplicates().shape[0]
        ),
        "minimum_trajectory_length": int(lengths.min()),
        "maximum_trajectory_length": int(lengths.max()),
        "negative_speed_count": int(
            ((cleaned["v_mps"] < 0) | (cleaned["v_next_mps"] < 0)).sum()
        ),
        "moving_positive_acceleration_count": int(
            (
                (cleaned["v_mps"] > args.stop_speed_mps)
                & (cleaned["a_mps2"] > 0.5)
            ).sum()
        ),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

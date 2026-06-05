from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from .physics import generate_synthetic_sequence_dataset


FEATURE_COLS = ["v_mps", "a_mps2", "pressure_MPa", "mu"]
TARGET_COLS = ["v_next_mps", "a_next_mps2"]


@dataclass
class Normalizer:
    x_mean: np.ndarray
    x_std: np.ndarray
    y_mean: np.ndarray
    y_std: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray, y: np.ndarray) -> "Normalizer":
        x_flat = x.reshape(-1, x.shape[-1])
        return cls(
            x_mean=x_flat.mean(axis=0).astype(np.float32),
            x_std=(x_flat.std(axis=0) + 1e-8).astype(np.float32),
            y_mean=y.mean(axis=0).astype(np.float32),
            y_std=(y.std(axis=0) + 1e-8).astype(np.float32),
        )

    def normalize_x(self, x: np.ndarray) -> np.ndarray:
        return (x - self.x_mean) / self.x_std

    def normalize_y(self, y: np.ndarray) -> np.ndarray:
        return (y - self.y_mean) / self.y_std

    def to_checkpoint(self) -> dict:
        return {
            "x_mean": self.x_mean,
            "x_std": self.x_std,
            "y_mean": self.y_mean,
            "y_std": self.y_std,
        }


class BrakeSequenceDataset(Dataset):
    def __init__(self, x: np.ndarray, y: np.ndarray, normalizer: Normalizer):
        self.x_raw = x.astype(np.float32)
        self.y_raw = y.astype(np.float32)
        self.x = normalizer.normalize_x(self.x_raw).astype(np.float32)
        self.y = normalizer.normalize_y(self.y_raw).astype(np.float32)

    def __len__(self) -> int:
        return self.x.shape[0]

    def __getitem__(self, idx: int):
        return (
            torch.from_numpy(self.x[idx]),
            torch.from_numpy(self.y[idx]),
            torch.from_numpy(self.x_raw[idx, -1]),
            torch.from_numpy(self.y_raw[idx]),
        )


def load_or_create_dataframe(
    path: Path,
    num_trajectories: int = 800,
    steps_per_trajectory: int = 120,
) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_synthetic_sequence_dataset(
        num_trajectories=num_trajectories,
        steps_per_trajectory=steps_per_trajectory,
    )
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def validate_columns(df: pd.DataFrame):
    missing = [col for col in FEATURE_COLS + TARGET_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def build_sequences(df: pd.DataFrame, sequence_len: int) -> tuple[np.ndarray, np.ndarray]:
    validate_columns(df)
    x_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []

    if {"trajectory_id", "step"}.issubset(df.columns):
        for _, group in df.sort_values(["trajectory_id", "step"]).groupby("trajectory_id", sort=False):
            g = group.reset_index(drop=True)
            if len(g) < sequence_len:
                continue
            features = g[FEATURE_COLS].to_numpy(dtype=np.float32)
            targets = g[TARGET_COLS].to_numpy(dtype=np.float32)
            for end in range(sequence_len - 1, len(g)):
                x_list.append(features[end - sequence_len + 1 : end + 1])
                y_list.append(targets[end])
    else:
        if sequence_len != 1:
            raise ValueError(
                "sequence_len > 1 requires trajectory_id and step columns. "
                "Use data/brake_sequence_dataset.csv or CarSim trajectory exports."
            )
        x_list = [row[FEATURE_COLS].to_numpy(dtype=np.float32).reshape(1, -1) for _, row in df.iterrows()]
        y_list = [row[TARGET_COLS].to_numpy(dtype=np.float32) for _, row in df.iterrows()]

    if not x_list:
        raise ValueError("No sequences were built. Check trajectory lengths and sequence_len.")

    return np.stack(x_list), np.stack(y_list)


def split_indices(n: int, val_fraction: float = 0.2, seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = max(1, int(round(val_fraction * n)))
    return idx[n_val:], idx[:n_val]


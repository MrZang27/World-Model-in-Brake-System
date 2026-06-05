from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from brake_world_model.physics import BrakeParams, brake_step


FEATURE_COLS = ["v_mps", "a_mps2", "pressure_MPa", "mu"]


def parse_args():
    parser = argparse.ArgumentParser(description="Run a one-dimensional stopping MPC demo.")
    parser.add_argument("--model", type=Path, default=Path("models/world_model_lstm.pt"))
    parser.add_argument("--out-csv", type=Path, default=Path("results/mpc_stop_scenario.csv"))
    parser.add_argument("--out-fig", type=Path, default=Path("results/mpc_stop_scenario.png"))
    parser.add_argument("--initial-speed-kph", type=float, default=80.0)
    parser.add_argument("--initial-distance", type=float, default=65.0)
    parser.add_argument("--safe-distance", type=float, default=2.0)
    parser.add_argument("--mu", type=float, default=0.6)
    parser.add_argument("--horizon", type=int, default=45)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--max-steps", type=int, default=180)
    parser.add_argument("--pressure-max", type=float, default=10.0)
    parser.add_argument("--w-distance", type=float, default=6.0)
    parser.add_argument("--w-decel", type=float, default=0.08)
    parser.add_argument("--w-smooth", type=float, default=0.015)
    parser.add_argument("--collision-penalty", type=float, default=10000.0)
    parser.add_argument("--not-stop-penalty", type=float, default=35.0)
    parser.add_argument("--seed", type=int, default=23)
    return parser.parse_args()


class LearnedPredictor:
    def __init__(self, checkpoint_path: Path):
        import torch

        from brake_world_model.models import SequenceWorldModel

        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        self.sequence_len = int(checkpoint["sequence_len"])
        self.dt = float(checkpoint.get("dt", 0.05))
        self.feature_cols = checkpoint.get("feature_cols", FEATURE_COLS)
        self.normalizer = checkpoint["normalizer"]
        self.model = SequenceWorldModel(**checkpoint["model_config"])
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()

    def predict(self, history_batch: np.ndarray) -> np.ndarray:
        x_mean = self.normalizer["x_mean"]
        x_std = self.normalizer["x_std"]
        y_mean = self.normalizer["y_mean"]
        y_std = self.normalizer["y_std"]
        import torch

        x_norm = (history_batch.astype(np.float32) - x_mean) / x_std
        with torch.no_grad():
            y_norm = self.model(torch.from_numpy(x_norm)).numpy()
        y = y_norm * y_std + y_mean
        y[:, 0] = np.maximum(y[:, 0], 0.0)
        return y


def make_pressure_candidates(samples: int, horizon: int, pressure_max: float, previous_pressure: float, rng):
    raw = rng.uniform(0.0, pressure_max, size=(samples, horizon))
    smooth = np.empty_like(raw)
    smooth[:, 0] = 0.65 * previous_pressure + 0.35 * raw[:, 0]
    for k in range(1, horizon):
        smooth[:, k] = 0.74 * smooth[:, k - 1] + 0.26 * raw[:, k]

    deterministic = np.vstack(
        [
            np.zeros(horizon),
            np.full(horizon, previous_pressure),
            np.full(horizon, 0.35 * pressure_max),
            np.full(horizon, 0.65 * pressure_max),
            np.linspace(previous_pressure, pressure_max, horizon),
            np.linspace(pressure_max, 0.2 * pressure_max, horizon),
        ]
    )
    return np.vstack([smooth, deterministic])


def rollout_candidates(predictor, history, distance, candidates, mu, args, params: BrakeParams):
    n, horizon = candidates.shape
    distances = np.full(n, distance, dtype=np.float32)
    speeds = np.full(n, history[-1][0], dtype=np.float32)
    accelerations = np.full(n, history[-1][1], dtype=np.float32)
    stopped_distance = np.full(n, np.nan, dtype=np.float32)
    max_decel = np.zeros(n, dtype=np.float32)
    pressure_smooth_cost = np.zeros(n, dtype=np.float32)
    collided = np.zeros(n, dtype=bool)

    history_batch = np.repeat(np.array(history, dtype=np.float32)[None, :, :], n, axis=0)
    prev_pressure = history[-1][2]

    for k in range(horizon):
        pressure = candidates[:, k].astype(np.float32)
        pressure_smooth_cost += (pressure - prev_pressure) ** 2
        prev_pressure = pressure

        current_features = np.stack([speeds, accelerations, pressure, np.full(n, mu, dtype=np.float32)], axis=1)
        history_batch = np.concatenate([history_batch[:, 1:, :], current_features[:, None, :]], axis=1)

        if predictor is None:
            v_next, a_next, _, _ = brake_step(speeds, pressure, mu, params)
            pred = np.stack([v_next, a_next], axis=1)
        else:
            pred = predictor.predict(history_batch)

        v_next = np.maximum(pred[:, 0], 0.0)
        a_next = np.minimum(pred[:, 1], 0.0)
        travel = np.maximum(speeds * params.dt + 0.5 * a_next * params.dt**2, 0.0)
        distances -= travel
        collided |= distances < 0.0
        max_decel = np.maximum(max_decel, np.abs(a_next))

        just_stopped = (v_next <= 0.05) & np.isnan(stopped_distance)
        stopped_distance[just_stopped] = distances[just_stopped]
        speeds = v_next
        accelerations = a_next

    final_distance = np.where(np.isnan(stopped_distance), distances, stopped_distance)
    terminal_speed = speeds
    distance_cost = args.w_distance * (final_distance - args.safe_distance) ** 2
    comfort_cost = args.w_decel * max_decel**2
    smooth_cost = args.w_smooth * pressure_smooth_cost / max(horizon, 1)
    collision_cost = args.collision_penalty * collided.astype(np.float32)
    not_stop_cost = args.not_stop_penalty * terminal_speed**2
    cost = distance_cost + comfort_cost + smooth_cost + collision_cost + not_stop_cost
    return cost


def select_pressure(predictor, history, distance, mu, previous_pressure, args, params, rng):
    candidates = make_pressure_candidates(args.samples, args.horizon, args.pressure_max, previous_pressure, rng)
    cost = rollout_candidates(predictor, history, distance, candidates, mu, args, params)
    best_idx = int(np.argmin(cost))
    return float(np.clip(candidates[best_idx, 0], 0.0, args.pressure_max)), float(cost[best_idx])


def plot_result(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(8, 8), sharex=True)
    axes[0].plot(df["time_s"], df["distance_m"], label="distance")
    axes[0].axhline(df["safe_distance_m"].iloc[0], linestyle="--", color="tab:red", label="safe distance")
    axes[0].set_ylabel("x (m)")
    axes[0].legend()
    axes[1].plot(df["time_s"], df["v_mps"] * 3.6)
    axes[1].set_ylabel("v (km/h)")
    axes[2].plot(df["time_s"], df["a_mps2"])
    axes[2].set_ylabel("a (m/s^2)")
    axes[3].step(df["time_s"], df["pressure_MPa"], where="post")
    axes[3].set_ylabel("P (MPa)")
    axes[3].set_xlabel("time (s)")
    for ax in axes:
        ax.grid(True, alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    params = BrakeParams()

    predictor = None
    if args.model.exists():
        try:
            predictor = LearnedPredictor(args.model)
            sequence_len = predictor.sequence_len
            print(f"using learned predictor: {args.model}")
        except Exception as exc:
            sequence_len = 5
            print(f"learned predictor unavailable, using physics fallback. reason: {exc}")
    else:
        sequence_len = 5
        print(f"model not found, using physics predictor fallback: {args.model}")

    v = args.initial_speed_kph / 3.6
    a = 0.0
    distance = args.initial_distance
    pressure = 0.0
    history = deque([[v, a, pressure, args.mu] for _ in range(sequence_len)], maxlen=sequence_len)
    rows = []

    for step in range(args.max_steps):
        time_s = step * params.dt
        rows.append(
            {
                "step": step,
                "time_s": time_s,
                "distance_m": distance,
                "safe_distance_m": args.safe_distance,
                "v_mps": v,
                "a_mps2": a,
                "pressure_MPa": pressure,
                "mu": args.mu,
            }
        )

        if v <= 0.05 or distance <= 0.0:
            break

        pressure, _ = select_pressure(predictor, list(history), distance, args.mu, pressure, args, params, rng)
        v_next, a_next, _, _ = brake_step(v, pressure, args.mu, params)
        travel = max(v * params.dt + 0.5 * float(a_next) * params.dt**2, 0.0)
        distance -= travel
        v, a = float(v_next), float(a_next)
        history.append([v, a, pressure, args.mu])

    df = pd.DataFrame(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    plot_result(df, args.out_fig)

    final = df.iloc[-1]
    print(f"saved scenario: {args.out_csv}")
    print(f"saved figure: {args.out_fig}")
    print(
        "final "
        f"distance={final['distance_m']:.2f} m, "
        f"speed={final['v_mps'] * 3.6:.2f} km/h, "
        f"steps={len(df)}"
    )


if __name__ == "__main__":
    main()

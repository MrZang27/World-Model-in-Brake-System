from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BrakeParams:
    m: float = 1800.0
    g: float = 9.81
    k_brake: float = 3500.0
    dt: float = 0.05
    min_speed: float = 0.0
    slip_pressure_ratio: float = 0.95
    max_comfort_decel: float = 8.0


def brake_step(v_mps, pressure_mpa, mu, params: BrakeParams = BrakeParams()):
    """Vectorized one-step longitudinal braking dynamics."""
    v = np.maximum(v_mps, params.min_speed)
    pressure = np.maximum(pressure_mpa, 0.0)
    mu_safe = np.maximum(mu, 0.01)

    f_brake = params.k_brake * pressure
    f_max = mu_safe * params.m * params.g
    f_actual = np.minimum(f_brake, f_max)

    a_next = -f_actual / params.m
    v_next = np.maximum(v + a_next * params.dt, params.min_speed)
    utilization = f_brake / np.maximum(f_max, np.finfo(float).eps)
    slip_risk = utilization > params.slip_pressure_ratio
    return v_next, a_next, utilization, slip_risk


def generate_synthetic_sequence_dataset(
    num_trajectories: int = 800,
    steps_per_trajectory: int = 120,
    seed: int = 19,
    params: BrakeParams = BrakeParams(),
):
    """Generate trajectory data with the same schema expected from CarSim."""
    rng = np.random.default_rng(seed)
    rows = []
    mu_choices = np.array([0.2, 0.4, 0.6, 0.8], dtype=float)

    for trajectory_id in range(num_trajectories):
        v = rng.uniform(20.0, 120.0) / 3.6
        a = 0.0
        base_mu = float(rng.choice(mu_choices))
        next_mu = float(rng.choice(mu_choices))
        change_step = int(rng.integers(max(1, int(0.35 * steps_per_trajectory)), max(2, int(0.75 * steps_per_trajectory))))
        pressure = float(rng.uniform(0.0, 10.0))
        target_pressure = float(rng.uniform(0.0, 10.0))
        segment_left = int(rng.integers(12, 29))

        for step in range(steps_per_trajectory):
            segment_left -= 1
            if segment_left <= 0:
                target_pressure = float(rng.uniform(0.0, 10.0))
                segment_left = int(rng.integers(12, 29))

            pressure = float(np.clip(0.86 * pressure + 0.14 * target_pressure + 0.25 * rng.normal(), 0.0, 10.0))
            mu = base_mu if step < change_step else next_mu
            v_next, a_next, utilization, slip_risk = brake_step(v, pressure, mu, params)
            rows.append(
                {
                    "trajectory_id": trajectory_id,
                    "step": step,
                    "time_s": step * params.dt,
                    "v_mps": float(v),
                    "a_mps2": float(a),
                    "pressure_MPa": float(pressure),
                    "mu": float(mu),
                    "v_next_mps": float(v_next),
                    "a_next_mps2": float(a_next),
                    "brake_utilization": float(utilization),
                    "slip_risk": bool(slip_risk),
                }
            )
            v, a = float(v_next), float(a_next)

    return rows


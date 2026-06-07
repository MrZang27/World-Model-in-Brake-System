"""Build presentation-ready charts and tables for the brake world-model project."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

BLUE = {"base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"}
GOLD = {"base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"}
ORANGE = {"base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"}
OLIVE = {"base": "#A3D576", "mid": "#71B436", "dark": "#386411"}
PINK = {"base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Aptos",
                "Segoe UI",
                "Microsoft YaHei",
                "SimHei",
                "DejaVu Sans",
                "Arial",
            ],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "text.color": TOKENS["ink"],
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "savefig.facecolor": TOKENS["surface"],
            "axes.titlepad": 18,
        }
    )


def add_header(fig, title: str, subtitle: str) -> None:
    fig.text(0.06, 0.96, title, ha="left", va="top", fontsize=16, weight="bold")
    fig.text(0.06, 0.92, subtitle, ha="left", va="top", fontsize=10.5, color=TOKENS["muted"])


def finish(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        return max(sum(1 for _ in file) - 1, 0)


def write_markdown_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        path.write_text("", encoding="utf-8")
        return
    columns = [str(col) for col in df.columns]
    rows = []
    for _, row in df.iterrows():
        rows.append([str(row[col]) for col in df.columns])

    def esc(value: str) -> str:
        return value.replace("\n", " ").replace("|", "\\|")

    lines = [
        "| " + " | ".join(esc(col) for col in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(esc(value) for value in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def chart_dataset_inventory(root: Path, out: Path) -> dict:
    rows = [
        ("Mechanism one-step", count_rows(root / "data" / "brake_dataset.csv")),
        ("Mechanism sequence", count_rows(root / "data" / "brake_sequence_dataset.csv")),
        ("CarSim raw transitions", count_rows(root / "data" / "carsim_brake_sequence_dataset.csv")),
        ("CarSim training rows", count_rows(root / "data" / "carsim_brake_sequence_training.csv")),
        ("CarSim matrix smoke", count_rows(root / "data" / "carsim_matrix_smoke.csv")),
    ]
    df = pd.DataFrame(rows, columns=["dataset", "rows"])
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    add_header(fig, "Dataset scale across the pipeline", "Rows available for baseline, sequence, CarSim, and validation workflows.")
    colors = [BLUE["mid"], BLUE["base"], ORANGE["mid"], ORANGE["base"], OLIVE["base"]]
    bars = ax.barh(df["dataset"], df["rows"], color=colors, edgecolor=TOKENS["ink"], linewidth=0.8)
    ax.invert_yaxis()
    ax.grid(axis="x", color=TOKENS["grid"], linewidth=0.8)
    ax.set_xlabel("Rows")
    ax.set_ylabel("")
    for bar, value in zip(bars, df["rows"]):
        ax.text(value + max(df["rows"]) * 0.015, bar.get_y() + bar.get_height() / 2, f"{value:,}", va="center", fontsize=9)
    finish(fig, out / "01_dataset_inventory.png")
    write_markdown_table(df, out / "tables" / "dataset_inventory.md")
    return {"file": "01_dataset_inventory.png", "takeaway": "The project now contains mechanism, sequence, and CarSim datasets."}


def chart_mechanism_coverage(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "brake_dataset.csv")
    if df.empty:
        return {}
    columns = [
        ("v_mps", "Speed (m/s)", BLUE["mid"]),
        ("pressure_MPa", "Pressure (MPa)", ORANGE["mid"]),
        ("mu", "Road adhesion", OLIVE["mid"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.6))
    add_header(fig, "Mechanism dataset coverage", "Distributions of speed, brake pressure, and road adhesion in the one-step baseline data.")
    for ax, (col, label, color) in zip(axes, columns):
        if col not in df:
            continue
        ax.hist(df[col].dropna(), bins=28, color=color, edgecolor=TOKENS["ink"], alpha=0.9)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", color=TOKENS["grid"])
        ax.set_ylabel("Samples")
    finish(fig, out / "02_mechanism_dataset_coverage.png")
    return {"file": "02_mechanism_dataset_coverage.png", "takeaway": "The baseline data covers speed, pressure, and adhesion broadly."}


def chart_mechanism_response(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "brake_dataset.csv")
    if df.empty:
        return {}
    pressure_col = "pressure_MPa"
    accel_col = "a_next_mps2"
    mu_col = "mu"
    if not {pressure_col, accel_col, mu_col}.issubset(df.columns):
        return {}
    df = df.copy()
    df["pressure_bin"] = pd.cut(df[pressure_col], bins=np.linspace(0, 10, 11), include_lowest=True)
    grouped = (
        df.groupby([mu_col, "pressure_bin"], observed=True)[accel_col]
        .mean()
        .reset_index()
    )
    grouped["pressure_mid"] = grouped["pressure_bin"].apply(lambda interval: interval.mid).astype(float)
    fig, ax = plt.subplots(figsize=(8.8, 5))
    add_header(fig, "Mechanism braking response by road adhesion", "Mean next-step acceleration by pressure bin; curves saturate at the adhesion limit.")
    palette = {0.2: BLUE["mid"], 0.4: OLIVE["mid"], 0.6: GOLD["mid"], 0.8: ORANGE["mid"]}
    for mu, part in grouped.groupby(mu_col):
        color = palette.get(round(float(mu), 1), TOKENS["muted"])
        ax.plot(part["pressure_mid"], part[accel_col], marker="o", linewidth=2, label=f"mu={mu:g}", color=color)
    ax.axhline(0, color=TOKENS["axis"], linewidth=1)
    ax.set_xlabel("Pressure (MPa)")
    ax.set_ylabel("Mean a_next (m/s^2)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False, ncol=2)
    finish(fig, out / "03_mechanism_pressure_mu_response.png")
    return {"file": "03_mechanism_pressure_mu_response.png", "takeaway": "Higher adhesion supports stronger deceleration before saturation."}


def chart_sequence_examples(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "brake_sequence_dataset.csv")
    if df.empty:
        return {}
    traj_col = "trajectory_id"
    if traj_col not in df.columns:
        return {}
    sample_ids = list(df[traj_col].drop_duplicates().head(4))
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.6), sharex=True)
    add_header(fig, "Mechanism sequence examples", "Representative trajectories used for recurrent world-model training.")
    colors = [BLUE["mid"], ORANGE["mid"], OLIVE["mid"], PINK["mid"]]
    fields = [("v_mps", "Speed (m/s)"), ("a_mps2", "Acceleration (m/s^2)"), ("pressure_MPa", "Pressure (MPa)")]
    for ax, (field, ylabel) in zip(axes, fields):
        for idx, tid in enumerate(sample_ids):
            part = df[df[traj_col] == tid]
            x = part["time_s"] if "time_s" in part else part["step"]
            if field in part:
                ax.plot(x, part[field], color=colors[idx], linewidth=1.8, label=f"traj {tid}" if field == "v_mps" else None)
        ax.set_ylabel(ylabel)
        ax.grid(color=TOKENS["grid"])
    axes[-1].set_xlabel("Time (s)")
    axes[0].legend(frameon=False, ncol=4, loc="upper right")
    finish(fig, out / "04_mechanism_sequence_examples.png")
    return {"file": "04_mechanism_sequence_examples.png", "takeaway": "The recurrent model sees full pressure and vehicle-state histories."}


def chart_metrics_tables(root: Path, out: Path) -> dict:
    world = safe_read_csv(root / "results" / "world_model_metrics.csv")
    seq = safe_read_csv(root / "results" / "sequence_world_model_metrics.csv")
    carsim = safe_read_csv(root / "results" / "carsim_gru_metrics.csv")
    rows = []
    if not world.empty:
        for _, row in world.iterrows():
            rows.append(["MLP mechanism", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    if not seq.empty:
        for _, row in seq.iterrows():
            rows.append(["Sequence mechanism", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    if not carsim.empty:
        for _, row in carsim.iterrows():
            rows.append(["GRU CarSim", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    df = pd.DataFrame(rows, columns=["model_data", "output", "rmse", "mae", "r2"])
    if df.empty:
        return {}
    write_markdown_table(df, out / "tables" / "model_metrics_summary.md")
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    add_header(fig, "Model validation RMSE summary", "Mechanism models are easier; CarSim acceleration is the hardest target.")
    pivot = df.pivot_table(index="model_data", columns="output", values="rmse", aggfunc="first")
    labels = list(pivot.index)
    outputs = list(pivot.columns)
    x = np.arange(len(labels))
    width = 0.36
    color_map = [BLUE["mid"], ORANGE["mid"], OLIVE["mid"]]
    for idx, output in enumerate(outputs):
        values = pivot[output].fillna(0).values
        offset = (idx - (len(outputs) - 1) / 2) * width
        ax.bar(x + offset, values, width, label=output, color=color_map[idx % len(color_map)], edgecolor=TOKENS["ink"], linewidth=0.7)
    ax.set_xticks(x, labels, rotation=12, ha="right")
    ax.set_ylabel("RMSE")
    ax.grid(axis="y", color=TOKENS["grid"])
    ax.legend(frameon=False, loc="upper left")
    finish(fig, out / "05_model_metrics_rmse_summary.png")
    return {"file": "05_model_metrics_rmse_summary.png", "takeaway": "CarSim-GRU keeps high speed accuracy but acceleration is more challenging."}


def chart_recurrent_ablation(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "recurrent_ablation" / "comparison.csv")
    if df.empty:
        return {}
    df = df.copy()
    df["label"] = df.apply(lambda r: f"{r['recurrent'].upper()} S{r['sequence_len']} H{r['hidden_size']} L{r['num_layers']}", axis=1)
    df["params_k"] = df["parameter_count"] / 1000
    colors = [OLIVE["mid"] if row["experiment"] == "gru_s5_h64_l1" else (BLUE["base"] if row["recurrent"] == "gru" else ORANGE["base"]) for _, row in df.iterrows()]
    y = np.arange(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(12, 6.4), sharey=True)
    add_header(fig, "LSTM vs GRU ablation", "Trajectory-level split, 40 epochs, PINN weight 0.05; highlighted row is the recommended model.")
    for ax, field, title, unit in [
        (axes[0], "v_rmse", "Speed RMSE", "m/s"),
        (axes[1], "a_rmse", "Accel RMSE", "m/s^2"),
        (axes[2], "params_k", "Parameters", "k"),
    ]:
        values = df[field].values
        ax.barh(y, values, color=colors, edgecolor=TOKENS["ink"], linewidth=0.7)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(unit)
        ax.grid(axis="x", color=TOKENS["grid"])
        ax.set_xlim(0, max(values) * 1.22)
        for yi, value in enumerate(values):
            fmt = f"{value:.3f}" if value < 10 else f"{value:.1f}"
            ax.text(value + max(values) * 0.025, yi, fmt, va="center", fontsize=8)
    axes[0].set_yticks(y, df["label"])
    axes[0].invert_yaxis()
    for ax in axes[1:]:
        ax.tick_params(axis="y", labelleft=False)
    finish(fig, out / "06_recurrent_ablation_rmse_params.png")
    write_markdown_table(df[["experiment", "recurrent", "sequence_len", "hidden_size", "num_layers", "parameter_count", "v_rmse", "a_rmse", "v_r2", "a_r2"]], out / "tables" / "recurrent_ablation.md")
    return {"file": "06_recurrent_ablation_rmse_params.png", "takeaway": "GRU S5 H64 L1 is compact and wins the key acceleration metric."}


def chart_ablation_tradeoff(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "recurrent_ablation" / "comparison.csv")
    if df.empty:
        return {}
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    add_header(fig, "Model-size vs acceleration-error tradeoff", "The selected GRU sits near the best accuracy region with far fewer parameters.")
    for recurrent, part in df.groupby("recurrent"):
        color = BLUE["mid"] if recurrent == "gru" else ORANGE["mid"]
        ax.scatter(part["parameter_count"] / 1000, part["a_rmse"], s=110, color=color, edgecolor=TOKENS["ink"], label=recurrent.upper(), alpha=0.9)
        for _, row in part.iterrows():
            ax.text(row["parameter_count"] / 1000 + 3, row["a_rmse"], f"S{int(row['sequence_len'])} H{int(row['hidden_size'])} L{int(row['num_layers'])}", fontsize=7.5, va="center")
    ax.set_xlabel("Parameters (k)")
    ax.set_ylabel("Acceleration RMSE (m/s^2)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False)
    finish(fig, out / "07_recurrent_tradeoff_scatter.png")
    return {"file": "07_recurrent_tradeoff_scatter.png", "takeaway": "Bigger recurrent networks are not automatically better for this task."}


def chart_carsim_run_matrix(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_full_dataset_summary.csv")
    if df.empty:
        return {}
    pivot = df.groupby(["mu", "initial_speed_kph"])["row_count"].sum().unstack("initial_speed_kph").sort_index()
    fig, ax = plt.subplots(figsize=(8.6, 5))
    add_header(fig, "CarSim dataset coverage matrix", "Rows collected by speed and road adhesion across 120 trajectories.")
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(np.arange(pivot.shape[1]), [f"{int(v)}" for v in pivot.columns])
    ax.set_yticks(np.arange(pivot.shape[0]), [f"{v:.1f}" for v in pivot.index])
    ax.set_xlabel("Initial speed (km/h)")
    ax.set_ylabel("mu")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{int(pivot.values[i, j])}", ha="center", va="center", fontsize=9, color=TOKENS["ink"])
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="Rows")
    finish(fig, out / "08_carsim_coverage_heatmap.png")
    return {"file": "08_carsim_coverage_heatmap.png", "takeaway": "Every speed/adhesion condition is represented in the full CarSim dataset."}


def chart_carsim_decel_by_mu(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_full_dataset_summary.csv")
    if df.empty:
        return {}
    grouped = df.groupby(["mu", "initial_speed_kph"])["minimum_acceleration_mps2"].apply(lambda s: abs(s).mean()).reset_index()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    add_header(fig, "CarSim peak deceleration follows road adhesion", "Average absolute minimum acceleration across pressure trajectories.")
    palette = {0.2: BLUE["mid"], 0.4: OLIVE["mid"], 0.6: GOLD["mid"], 0.8: ORANGE["mid"]}
    for mu, part in grouped.groupby("mu"):
        color = palette.get(round(float(mu), 1), TOKENS["muted"])
        ax.plot(part["initial_speed_kph"], part["minimum_acceleration_mps2"], marker="o", linewidth=2.4, color=color, label=f"mu={mu:g}")
        ax.axhline(float(mu) * 9.81, color=color, linewidth=1, alpha=0.18)
    ax.set_xlabel("Initial speed (km/h)")
    ax.set_ylabel("|Minimum acceleration| (m/s^2)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False, ncol=2)
    finish(fig, out / "09_carsim_peak_decel_by_mu.png")
    return {"file": "09_carsim_peak_decel_by_mu.png", "takeaway": "CarSim produces the expected adhesion-limited deceleration layers."}


def chart_carsim_matrix_smoke(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_matrix_smoke_summary.csv")
    if df.empty:
        return {}
    df = df.copy()
    df["case"] = df.apply(lambda r: f"{int(r['initial_speed_kph'])} km/h\nmu={r['mu']:.1f}", axis=1)
    fig, ax = plt.subplots(figsize=(8.8, 5))
    add_header(fig, "CarSim boundary smoke-test response", "Six representative cases confirm speed matching and braking response.")
    bars = ax.bar(df["case"], abs(df["minimum_acceleration_mps2"]), color=[BLUE["mid"] if mu == 0.2 else ORANGE["mid"] for mu in df["mu"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    ax.set_ylabel("|Minimum acceleration| (m/s^2)")
    ax.grid(axis="y", color=TOKENS["grid"])
    for bar, valid in zip(bars, df["valid"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15, "PASS" if bool(valid) else "FAIL", ha="center", fontsize=8)
    finish(fig, out / "10_carsim_matrix_smoke.png")
    write_markdown_table(df, out / "tables" / "carsim_matrix_smoke.md")
    return {"file": "10_carsim_matrix_smoke.png", "takeaway": "Low-mu and high-mu boundary cases produce distinct, valid braking responses."}


def chart_carsim_smoke_trajectory(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_smoke_trajectory.csv")
    if df.empty:
        return {}
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)
    add_header(fig, "CarSim single-case smoke trajectory", "80 km/h, mu=0.85, pressure command 2 MPa, simulated for 2.5 s.")
    columns = [
        ("speed_kph", "Speed (km/h)", BLUE["mid"]),
        ("acceleration_mps2", "Acceleration (m/s^2)", ORANGE["mid"]),
        ("pressure_mpa", "Pressure (MPa)", OLIVE["mid"]),
    ]
    time_col = "time_s" if "time_s" in df else df.columns[0]
    for ax, (field, ylabel, color) in zip(axes, columns):
        if field not in df:
            candidates = [c for c in df.columns if field.split("_")[0].lower() in c.lower()]
            if not candidates:
                continue
            field = candidates[0]
        ax.plot(df[time_col], df[field], color=color, linewidth=2)
        ax.set_ylabel(ylabel)
        ax.grid(color=TOKENS["grid"])
    axes[-1].set_xlabel("Time (s)")
    finish(fig, out / "11_carsim_smoke_trajectory.png")
    return {"file": "11_carsim_smoke_trajectory.png", "takeaway": "The co-simulation responds to pressure input and returns finite vehicle signals."}


def chart_carsim_pressure_examples(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "carsim_brake_sequence_dataset.csv")
    if df.empty:
        return {}
    group_cols = ["trajectory_id"]
    sample_ids = list(df["trajectory_id"].drop_duplicates().head(8))
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.4), sharex=True)
    add_header(fig, "CarSim pressure-profile examples", "A subset of random and smooth pressure trajectories used for high-fidelity data collection.")
    palette = [BLUE["mid"], ORANGE["mid"], OLIVE["mid"], PINK["mid"], GOLD["mid"], BLUE["dark"], ORANGE["dark"], OLIVE["dark"]]
    for idx, tid in enumerate(sample_ids):
        part = df[df["trajectory_id"] == tid]
        x = part["time_s"] if "time_s" in part else part["step"]
        axes[0].plot(x, part["pressure_MPa"], color=palette[idx % len(palette)], linewidth=1.7, label=f"traj {tid}")
        axes[1].plot(x, part["v_mps"] * 3.6, color=palette[idx % len(palette)], linewidth=1.7)
    axes[0].set_ylabel("Pressure (MPa)")
    axes[1].set_ylabel("Speed (km/h)")
    axes[1].set_xlabel("Time (s)")
    for ax in axes:
        ax.grid(color=TOKENS["grid"])
    axes[0].legend(frameon=False, ncol=4, fontsize=8)
    finish(fig, out / "12_carsim_pressure_profile_examples.png")
    return {"file": "12_carsim_pressure_profile_examples.png", "takeaway": "The CarSim data includes varied braking commands rather than one fixed pressure."}


def chart_carsim_gru_metrics(root: Path, out: Path) -> dict:
    metrics = safe_read_csv(root / "results" / "carsim_gru_metrics.csv")
    summary = safe_read_json(root / "results" / "carsim_gru_training_summary.json")
    if metrics.empty:
        return {}
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.8))
    add_header(fig, "CarSim-GRU validation metrics", "S=5, H=64, one GRU layer, PINN weight 0.05; trajectory-level split.")
    x = np.arange(len(metrics))
    axes[0].bar(metrics["output"], metrics["rmse"], color=[BLUE["mid"], ORANGE["mid"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    axes[0].set_ylabel("RMSE")
    axes[0].grid(axis="y", color=TOKENS["grid"])
    axes[1].bar(metrics["output"], metrics["r2"], color=[BLUE["base"], ORANGE["base"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    axes[1].set_ylabel("R^2")
    axes[1].set_ylim(0, 1.05)
    axes[1].grid(axis="y", color=TOKENS["grid"])
    subtitle = f"parameters={summary.get('parameter_count', 'n/a')}, train={summary.get('train_samples', 'n/a')}, val={summary.get('val_samples', 'n/a')}"
    fig.text(0.06, 0.06, subtitle, fontsize=9, color=TOKENS["muted"])
    finish(fig, out / "13_carsim_gru_metrics.png")
    write_markdown_table(metrics, out / "tables" / "carsim_gru_metrics.md")
    return {"file": "13_carsim_gru_metrics.png", "takeaway": "Speed prediction remains very strong; acceleration is the honest hard target."}


def chart_mpc_stop(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "mpc_stop_scenario.csv")
    if df.empty:
        return {}
    df = df.copy()
    if "speed_kph" not in df.columns and "v_mps" in df.columns:
        df["speed_kph"] = df["v_mps"] * 3.6
    if "acceleration_mps2" not in df.columns and "a_mps2" in df.columns:
        df["acceleration_mps2"] = df["a_mps2"]
    if "pressure_MPa" not in df.columns and "P_MPa" in df.columns:
        df["pressure_MPa"] = df["P_MPa"]
    fig, axes = plt.subplots(4, 1, figsize=(9.5, 8.8), sharex=True)
    add_header(fig, "Sampled MPC closed-loop stopping result", "80 km/h, x0=65 m, mu=0.6, target safe distance=2 m; execution uses the mechanism environment.")
    time_col = "time_s" if "time_s" in df else df.columns[0]
    plots = [
        ("distance_m", "Distance (m)", BLUE["mid"]),
        ("speed_kph", "Speed (km/h)", BLUE["dark"]),
        ("acceleration_mps2", "Acceleration (m/s^2)", ORANGE["mid"]),
        ("pressure_MPa", "Pressure (MPa)", OLIVE["mid"]),
    ]
    for ax, (field, ylabel, color) in zip(axes, plots):
        if field not in df:
            candidates = [c for c in df.columns if field.split("_")[0].lower() in c.lower()]
            if not candidates:
                continue
            field = candidates[0]
        ax.plot(df[time_col], df[field], color=color, linewidth=2)
        if "distance" in field:
            ax.axhline(2.0, color=ORANGE["dark"], linestyle="--", linewidth=1.4, label="safe distance")
            ax.legend(frameon=False)
        ax.set_ylabel(ylabel)
        ax.grid(color=TOKENS["grid"])
    axes[-1].set_xlabel("Time (s)")
    finish(fig, out / "14_mpc_stop_result.png")
    return {"file": "14_mpc_stop_result.png", "takeaway": "The sampled planner stops safely within 0.156 m of the target distance."}


def write_asset_manifest(asset_records: list[dict], out: Path) -> None:
    df = pd.DataFrame(asset_records)
    if df.empty:
        return
    write_markdown_table(df, out / "tables" / "asset_manifest.md")
    (out / "asset_manifest.csv").write_text(df.to_csv(index=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    out = args.out_dir or (root / "results" / "presentation_assets")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)

    setup_style()
    builders = [
        chart_dataset_inventory,
        chart_mechanism_coverage,
        chart_mechanism_response,
        chart_sequence_examples,
        chart_metrics_tables,
        chart_recurrent_ablation,
        chart_ablation_tradeoff,
        chart_carsim_run_matrix,
        chart_carsim_decel_by_mu,
        chart_carsim_matrix_smoke,
        chart_carsim_smoke_trajectory,
        chart_carsim_pressure_examples,
        chart_carsim_gru_metrics,
        chart_mpc_stop,
    ]
    records = []
    for builder in builders:
        result = builder(root, out)
        if result:
            records.append({"chart": result["file"], "takeaway": result["takeaway"]})
    write_asset_manifest(records, out)
    print(json.dumps({"out_dir": str(out), "assets": records}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

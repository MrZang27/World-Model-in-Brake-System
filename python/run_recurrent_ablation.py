from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CONFIGURATIONS = [
    {"sequence_len": 5, "hidden_size": 64, "num_layers": 1},
    {"sequence_len": 5, "hidden_size": 128, "num_layers": 2},
    {"sequence_len": 50, "hidden_size": 64, "num_layers": 1},
    {"sequence_len": 50, "hidden_size": 128, "num_layers": 2},
]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a reproducible LSTM/GRU ablation study."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/brake_sequence_dataset.csv"),
    )
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--pinn-weight", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/recurrent_ablation"),
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--no-promote",
        action="store_false",
        dest="promote",
        help="Do not copy the recommended GRU baseline to the default model paths.",
    )
    parser.set_defaults(promote=True)
    return parser.parse_args()


def experiment_name(recurrent: str, config: dict) -> str:
    return (
        f"{recurrent}_s{config['sequence_len']}"
        f"_h{config['hidden_size']}_l{config['num_layers']}"
    )


def run_experiment(args, recurrent: str, config: dict) -> dict:
    name = experiment_name(recurrent, config)
    experiment_dir = args.output_dir / name
    model_path = experiment_dir / "model.pt"
    metrics_path = experiment_dir / "metrics.csv"
    loss_path = experiment_dir / "loss.png"
    summary_path = experiment_dir / "summary.json"

    if args.force or not summary_path.exists():
        experiment_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(PROJECT_ROOT / "python" / "train_sequence_world_model.py"),
            "--data",
            str(args.data),
            "--out",
            str(model_path),
            "--metrics-out",
            str(metrics_path),
            "--loss-fig",
            str(loss_path),
            "--summary-out",
            str(summary_path),
            "--recurrent",
            recurrent,
            "--sequence-len",
            str(config["sequence_len"]),
            "--hidden-size",
            str(config["hidden_size"]),
            "--num-layers",
            str(config["num_layers"]),
            "--epochs",
            str(args.epochs),
            "--batch-size",
            str(args.batch_size),
            "--pinn-weight",
            str(args.pinn_weight),
            "--split-strategy",
            "trajectory",
            "--seed",
            str(args.seed),
        ]
        print(f"\n=== {name} ===", flush=True)
        subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    else:
        print(f"reuse completed experiment: {name}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = summary.pop("metrics")
    summary["experiment"] = name
    summary["v_rmse"] = metrics["rmse"][0]
    summary["a_rmse"] = metrics["rmse"][1]
    summary["v_r2"] = metrics["r2"][0]
    summary["a_r2"] = metrics["r2"][1]
    return summary


def plot_comparison(results: pd.DataFrame, output_path: Path):
    labels = [
        f"{row.recurrent.upper()}\n"
        f"S{row.sequence_len}-H{row.hidden_size}-L{row.num_layers}"
        for row in results.itertuples()
    ]
    x = np.arange(len(results))
    width = 0.38

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].bar(x - width / 2, results["v_rmse"], width, label="speed")
    axes[0].bar(x + width / 2, results["a_rmse"], width, label="acceleration")
    axes[0].set_ylabel("Validation RMSE")
    axes[0].grid(axis="y", alpha=0.3)
    axes[0].legend()

    axes[1].bar(x - width / 2, results["v_r2"], width, label="speed")
    axes[1].bar(x + width / 2, results["a_r2"], width, label="acceleration")
    axes[1].set_ylabel("Validation R2")
    axes[1].set_xticks(x, labels, rotation=25, ha="right")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].legend()

    fig.suptitle("LSTM vs GRU Ablation Study")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_report(results: pd.DataFrame, output_path: Path):
    best_speed = results.loc[results["v_rmse"].idxmin()]
    best_accel = results.loc[results["a_rmse"].idxmin()]
    best_mean_r2 = results.assign(
        mean_r2=(results["v_r2"] + results["a_r2"]) / 2
    ).sort_values("mean_r2", ascending=False).iloc[0]

    columns = [
        "experiment",
        "recurrent",
        "sequence_len",
        "hidden_size",
        "num_layers",
        "parameter_count",
        "elapsed_seconds",
        "v_rmse",
        "v_r2",
        "a_rmse",
        "a_r2",
    ]
    table = results[columns].copy()
    for column in ["elapsed_seconds", "v_rmse", "v_r2", "a_rmse", "a_r2"]:
        table[column] = table[column].map(lambda value: f"{value:.6f}")
    headers = list(table.columns)
    markdown_rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in table.itertuples(index=False, name=None):
        markdown_rows.append(
            "| " + " | ".join(str(value) for value in row) + " |"
        )

    lines = [
        "# LSTM/GRU Ablation Study",
        "",
        "All experiments use the same dataset, random seed, PINN weight,",
        "trajectory-level train/validation split, and number of epochs.",
        "",
        *markdown_rows,
        "",
        "## Best Configurations",
        "",
        f"- Lowest speed RMSE: `{best_speed['experiment']}` "
        f"({best_speed['v_rmse']:.6f})",
        f"- Lowest acceleration RMSE: `{best_accel['experiment']}` "
        f"({best_accel['a_rmse']:.6f})",
        f"- Highest mean R2: `{best_mean_r2['experiment']}` "
        f"({best_mean_r2['mean_r2']:.6f})",
        "",
        "Lower RMSE and higher R2 are better. Parameter count and training time",
        "should be considered together with predictive accuracy.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    if not args.data.is_absolute():
        args.data = PROJECT_ROOT / args.data
    if not args.output_dir.is_absolute():
        args.output_dir = PROJECT_ROOT / args.output_dir
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for recurrent in ("lstm", "gru"):
        for config in CONFIGURATIONS:
            records.append(run_experiment(args, recurrent, config))

    results = pd.DataFrame(records)
    results = results.sort_values(
        ["recurrent", "sequence_len", "hidden_size", "num_layers"]
    ).reset_index(drop=True)
    csv_path = args.output_dir / "comparison.csv"
    figure_path = args.output_dir / "comparison.png"
    report_path = args.output_dir / "report.md"
    results.to_csv(csv_path, index=False)
    plot_comparison(results, figure_path)
    write_report(results, report_path)

    if args.promote:
        baseline_dir = args.output_dir / "gru_s5_h64_l1"
        promoted_files = [
            (baseline_dir / "model.pt", PROJECT_ROOT / "models" / "world_model_gru.pt"),
            (
                baseline_dir / "metrics.csv",
                PROJECT_ROOT / "results" / "sequence_world_model_metrics.csv",
            ),
            (
                baseline_dir / "loss.png",
                PROJECT_ROOT / "results" / "sequence_training_loss.png",
            ),
            (
                baseline_dir / "summary.json",
                PROJECT_ROOT / "results" / "sequence_world_model_summary.json",
            ),
        ]
        for source, destination in promoted_files:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        print(f"promoted default GRU model: {promoted_files[0][1]}")

    print("\nAblation study complete.")
    print(results[
        [
            "experiment",
            "parameter_count",
            "elapsed_seconds",
            "v_rmse",
            "v_r2",
            "a_rmse",
            "a_r2",
        ]
    ].to_string(index=False))
    print(f"saved comparison: {csv_path}")
    print(f"saved figure: {figure_path}")
    print(f"saved report: {report_path}")


if __name__ == "__main__":
    main()

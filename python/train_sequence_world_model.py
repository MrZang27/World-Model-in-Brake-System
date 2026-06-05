from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader

    from brake_world_model.data import (
        FEATURE_COLS,
        TARGET_COLS,
        BrakeSequenceDataset,
        Normalizer,
        build_sequences,
        load_or_create_dataframe,
        split_indices,
    )
    from brake_world_model.models import SequenceWorldModel
except Exception as exc:  # pragma: no cover - import guard for local environment issues.
    raise SystemExit(
        "PyTorch failed to import. Install a working torch build, then rerun this script. "
        f"Original error: {exc}"
    ) from exc


def parse_args():
    parser = argparse.ArgumentParser(description="Train an LSTM/GRU brake-system world model.")
    parser.add_argument("--data", type=Path, default=Path("data/brake_sequence_dataset.csv"))
    parser.add_argument("--out", type=Path, default=Path("models/world_model_lstm.pt"))
    parser.add_argument("--metrics-out", type=Path, default=Path("results/sequence_world_model_metrics.csv"))
    parser.add_argument("--loss-fig", type=Path, default=Path("results/sequence_training_loss.png"))
    parser.add_argument("--sequence-len", type=int, default=5)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--recurrent", choices=["lstm", "gru"], default="lstm")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--pinn-weight", type=float, default=0.05)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--synthetic-trajectories", type=int, default=800)
    parser.add_argument("--synthetic-steps", type=int, default=120)
    return parser.parse_args()


def denormalize(y_norm: torch.Tensor, y_mean: torch.Tensor, y_std: torch.Tensor) -> torch.Tensor:
    return y_norm * y_std + y_mean


def evaluate(model, loader, y_mean, y_std, device):
    model.eval()
    preds = []
    targets = []
    with torch.no_grad():
        for x, _, _, y_raw in loader:
            y_pred_norm = model(x.to(device))
            y_pred = denormalize(y_pred_norm, y_mean, y_std).cpu().numpy()
            preds.append(y_pred)
            targets.append(y_raw.numpy())

    y_pred = np.concatenate(preds, axis=0)
    y_true = np.concatenate(targets, axis=0)
    err = y_pred - y_true
    mse = np.mean(err**2, axis=0)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(err), axis=0)
    ss_res = np.sum(err**2, axis=0)
    ss_tot = np.sum((y_true - y_true.mean(axis=0)) ** 2, axis=0)
    r2 = 1.0 - ss_res / np.maximum(ss_tot, 1e-12)
    return {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2}


def write_metrics(path: Path, metrics: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["output", "mse", "rmse", "mae", "r2"])
        for i, name in enumerate(TARGET_COLS):
            writer.writerow([name, metrics["mse"][i], metrics["rmse"][i], metrics["mae"][i], metrics["r2"][i]])


def plot_loss(path: Path, history: dict[str, list[float]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    plt.plot(history["train"], label="train")
    plt.plot(history["val"], label="validation")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(True, alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main():
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = load_or_create_dataframe(args.data, args.synthetic_trajectories, args.synthetic_steps)
    x, y = build_sequences(df, args.sequence_len)
    train_idx, val_idx = split_indices(len(x), args.val_fraction, args.seed)

    normalizer = Normalizer.fit(x[train_idx], y[train_idx])
    train_ds = BrakeSequenceDataset(x[train_idx], y[train_idx], normalizer)
    val_ds = BrakeSequenceDataset(x[val_idx], y[val_idx], normalizer)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SequenceWorldModel(
        input_size=len(FEATURE_COLS),
        hidden_size=args.hidden_size,
        output_size=len(TARGET_COLS),
        num_layers=args.num_layers,
        recurrent=args.recurrent,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()

    y_mean = torch.tensor(normalizer.y_mean, dtype=torch.float32, device=device)
    y_std = torch.tensor(normalizer.y_std, dtype=torch.float32, device=device)

    history = {"train": [], "val": []}
    best_val = float("inf")
    best_state = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses = []
        for x_batch, y_batch, x_last_raw, _ in train_loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)
            x_last_raw = x_last_raw.to(device)

            optimizer.zero_grad()
            y_pred_norm = model(x_batch)
            data_loss = mse(y_pred_norm, y_batch)

            y_pred = denormalize(y_pred_norm, y_mean, y_std)
            v_t = x_last_raw[:, 0]
            v_next_pred = y_pred[:, 0]
            a_next_pred = y_pred[:, 1]
            physics_v_next = torch.clamp(v_t + a_next_pred * args.dt, min=0.0)
            pinn_loss = torch.mean((v_next_pred - physics_v_next) ** 2)

            loss = data_loss + args.pinn_weight * pinn_loss
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            train_losses.append(float(loss.item()))

        model.eval()
        val_losses = []
        with torch.no_grad():
            for x_batch, y_batch, x_last_raw, _ in val_loader:
                x_batch = x_batch.to(device)
                y_batch = y_batch.to(device)
                x_last_raw = x_last_raw.to(device)
                y_pred_norm = model(x_batch)
                data_loss = mse(y_pred_norm, y_batch)
                y_pred = denormalize(y_pred_norm, y_mean, y_std)
                physics_v_next = torch.clamp(x_last_raw[:, 0] + y_pred[:, 1] * args.dt, min=0.0)
                pinn_loss = torch.mean((y_pred[:, 0] - physics_v_next) ** 2)
                val_losses.append(float((data_loss + args.pinn_weight * pinn_loss).item()))

        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses))
        history["train"].append(train_loss)
        history["val"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        if epoch == 1 or epoch % 5 == 0 or epoch == args.epochs:
            print(f"epoch={epoch:03d} train_loss={train_loss:.6f} val_loss={val_loss:.6f}")

    if best_state is not None:
        model.load_state_dict(best_state)

    metrics = evaluate(model, val_loader, y_mean, y_std, device)
    write_metrics(args.metrics_out, metrics)
    plot_loss(args.loss_fig, history)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "state_dict": model.state_dict(),
        "model_config": {
            "input_size": len(FEATURE_COLS),
            "hidden_size": args.hidden_size,
            "output_size": len(TARGET_COLS),
            "num_layers": args.num_layers,
            "recurrent": args.recurrent,
        },
        "feature_cols": FEATURE_COLS,
        "target_cols": TARGET_COLS,
        "sequence_len": args.sequence_len,
        "dt": args.dt,
        "normalizer": normalizer.to_checkpoint(),
        "metrics": metrics,
        "history": history,
    }
    torch.save(checkpoint, args.out)

    print(f"saved model: {args.out}")
    print(f"saved metrics: {args.metrics_out}")
    print(f"saved loss figure: {args.loss_fig}")


if __name__ == "__main__":
    main()

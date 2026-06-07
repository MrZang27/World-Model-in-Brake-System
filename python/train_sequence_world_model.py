from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg") ##使用非交互式后端，以便在没有显示环境的服务器上保存图像。
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
        split_group_indices,
        split_indices,
    )
    from brake_world_model.models import SequenceWorldModel
except Exception as exc:  # pragma: no cover - import guard for local environment issues.
    raise SystemExit(
        "PyTorch failed to import. Install a working torch build, then rerun this script. "
        f"Original error: {exc}"
    ) from exc


## 这个脚本的主要功能是训练一个基于LSTM或GRU的序列世界模型，用于预测制动系统的下一个状态。它包括数据加载、模型定义、训练循环、评估和结果保存等步骤。
def parse_args():
    parser = argparse.ArgumentParser(description="Train an LSTM/GRU brake-system world model.")
    parser.add_argument("--data", type=Path, default=Path("data/brake_sequence_dataset.csv"))
    parser.add_argument("--out", type=Path, default=Path("models/world_model_gru.pt"))
    parser.add_argument("--metrics-out", type=Path, default=Path("results/sequence_world_model_metrics.csv"))
    parser.add_argument("--loss-fig", type=Path, default=Path("results/sequence_training_loss.png"))
    parser.add_argument("--summary-out", type=Path, default=None)
    parser.add_argument("--sequence-len", type=int, default=5)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--recurrent", choices=["lstm", "gru"], default="gru")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--pinn-weight", type=float, default=0.05)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument(
        "--split-strategy",
        choices=["trajectory", "window"],
        default="trajectory",
        help="Use trajectory splitting to avoid leakage between overlapping windows.",
    )
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--synthetic-trajectories", type=int, default=800)
    parser.add_argument("--synthetic-steps", type=int, default=120)
    return parser.parse_args()


## 评估函数和辅助函数用于计算模型在验证集上的性能指标，并保存结果和训练曲线图。
def denormalize(y_norm: torch.Tensor, y_mean: torch.Tensor, y_std: torch.Tensor) -> torch.Tensor:
    return y_norm * y_std + y_mean

## 评估函数，计算模型在验证集上的MSE、RMSE、MAE和R²等指标。
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

## 写入评估指标到CSV文件。
def write_metrics(path: Path, metrics: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["output", "mse", "rmse", "mae", "r2"])
        for i, name in enumerate(TARGET_COLS):
            writer.writerow([name, metrics["mse"][i], metrics["rmse"][i], metrics["mae"][i], metrics["r2"][i]])

## 绘制训练和验证损失曲线，并保存为图像文件。
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

## 主函数，执行整个训练流程，包括数据准备、模型训练、评估和结果保存。
def main():
    args = parse_args() # 解析命令行参数，获取训练配置。
    start_time = time.perf_counter()
    torch.manual_seed(args.seed) # 设置PyTorch的随机种子，以确保结果可复现。
    np.random.seed(args.seed) # 设置NumPy的随机种子，以确保结果可复现。

    df = load_or_create_dataframe(args.data, args.synthetic_trajectories, args.synthetic_steps)# 加载数据集，如果数据文件不存在则生成合成数据。
    x, y, trajectory_ids = build_sequences(df, args.sequence_len)
    if args.split_strategy == "trajectory":
        train_idx, val_idx = split_group_indices(
            trajectory_ids, args.val_fraction, args.seed
        )
    else:
        train_idx, val_idx = split_indices(
            len(x), args.val_fraction, args.seed
        )

    normalizer = Normalizer.fit(x[train_idx], y[train_idx]) # 计算训练集的特征和目标的均值和标准差，用于数据归一化。
    train_ds = BrakeSequenceDataset(x[train_idx], y[train_idx], normalizer) # 创建训练数据集对象，包含原始数据和归一化后的数据。
    val_ds = BrakeSequenceDataset(x[val_idx], y[val_idx], normalizer) # 创建验证数据集对象，包含原始数据和归一化后的数据。
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True) # 创建训练数据加载器，支持批量加载和数据打乱。
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False) # 创建验证数据加载器，支持批量加载但不打乱数据。

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # 检测是否有可用的GPU，如果有则使用GPU，否则使用CPU。
    model = SequenceWorldModel(
        input_size=len(FEATURE_COLS),
        hidden_size=args.hidden_size,
        output_size=len(TARGET_COLS),
        num_layers=args.num_layers,
        recurrent=args.recurrent,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr) # 创建Adam优化器，用于更新模型参数，学习率由命令行参数指定。
    mse = nn.MSELoss() # 定义均方误差损失函数，用于计算模型预测与真实值之间的误差。
    parameter_count = sum(parameter.numel() for parameter in model.parameters())

    y_mean = torch.tensor(normalizer.y_mean, dtype=torch.float32, device=device) # 将目标变量的均值转换为PyTorch张量，并移动到指定设备（CPU或GPU）。
    y_std = torch.tensor(normalizer.y_std, dtype=torch.float32, device=device) # 将目标变量的标准差转换为PyTorch张量，并移动到指定设备（CPU或GPU）。

    history = {"train": [], "val": []}
    best_val = float("inf")
    best_state = None

    # 训练循环，迭代指定的训练轮数，每轮进行一次完整的训练和验证过程。
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses = []

        # 训练阶段，遍历训练数据加载器，计算损失并更新模型参数，同时记录训练损失。
        for x_batch, y_batch, x_last_raw, _ in train_loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)
            x_last_raw = x_last_raw.to(device)

            optimizer.zero_grad()
            y_pred_norm = model(x_batch)
            data_loss = mse(y_pred_norm, y_batch)

            y_pred = denormalize(y_pred_norm, y_mean, y_std)
            v_t = x_last_raw[:, 0]
            v_next_pred = y_pred[:, 0] # 模型预测的下一个速度。
            a_next_pred = y_pred[:, 1] # 模型预测的下一个加速度。
            # 基于当前速度和预测的加速度计算物理预测的下一个速度，使用clamp确保速度不为负数。
            physics_v_next = torch.clamp(v_t + a_next_pred * args.dt, min=0.0)
            # 物理信息损失，鼓励模型的速度预测与基于当前速度和加速度的物理预测一致。
            pinn_loss = torch.mean((v_next_pred - physics_v_next) ** 2)

            loss = data_loss + args.pinn_weight * pinn_loss
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            train_losses.append(float(loss.item()))

        # 验证阶段，评估模型在验证集上的性能，并记录训练和验证损失。
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
        
        # 计算当前轮的平均训练损失和验证损失，并更新历史记录和最佳模型状态。
        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses))
        history["train"].append(train_loss)
        history["val"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        if epoch == 1 or epoch % 5 == 0 or epoch == args.epochs:
            print(f"epoch={epoch:03d} train_loss={train_loss:.6f} val_loss={val_loss:.6f}")
    
    # 训练完成后，如果存在最佳模型状态，则加载该状态到模型中，以便进行最终评估和保存。
    if best_state is not None:
        model.load_state_dict(best_state)

    # 评估模型在验证集上的性能，并将结果保存到CSV文件和图像文件中，同时保存训练历史和模型检查点。
    metrics = evaluate(model, val_loader, y_mean, y_std, device)
    write_metrics(args.metrics_out, metrics)
    plot_loss(args.loss_fig, history)

    # 保存模型检查点，包括模型参数、配置、归一化参数、评估指标和训练历史等信息，以便后续加载和使用。
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
        "split_strategy": args.split_strategy,
        "parameter_count": parameter_count,
    }
    torch.save(checkpoint, args.out)

    elapsed_seconds = time.perf_counter() - start_time
    summary = {
        "recurrent": args.recurrent,
        "sequence_len": args.sequence_len,
        "hidden_size": args.hidden_size,
        "num_layers": args.num_layers,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "pinn_weight": args.pinn_weight,
        "split_strategy": args.split_strategy,
        "seed": args.seed,
        "device": str(device),
        "parameter_count": parameter_count,
        "train_samples": int(len(train_idx)),
        "val_samples": int(len(val_idx)),
        "train_trajectories": int(len(np.unique(trajectory_ids[train_idx]))),
        "val_trajectories": int(len(np.unique(trajectory_ids[val_idx]))),
        "best_val_loss": best_val,
        "elapsed_seconds": elapsed_seconds,
        "metrics": {
            key: [float(value) for value in values]
            for key, values in metrics.items()
        },
    }
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

    print(f"saved model: {args.out}")
    print(f"saved metrics: {args.metrics_out}")
    print(f"saved loss figure: {args.loss_fig}")
    if args.summary_out is not None:
        print(f"saved summary: {args.summary_out}")
    print(
        f"model={args.recurrent.upper()} parameters={parameter_count:,} "
        f"split={args.split_strategy} elapsed={elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":
    main()

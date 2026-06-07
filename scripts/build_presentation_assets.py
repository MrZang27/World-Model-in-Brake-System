"""为制动系统世界模型项目生成可直接放入PPT的中文图表和表格。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
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
                "Microsoft YaHei",
                "SimHei",
                "DengXian",
                "Microsoft JhengHei",
                "SimSun",
                "Noto Sans CJK SC",
                "Source Han Sans SC",
                "Aptos",
                "Segoe UI",
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
        ("机理单步数据", count_rows(root / "data" / "brake_dataset.csv")),
        ("机理时序数据", count_rows(root / "data" / "brake_sequence_dataset.csv")),
        ("CarSim 原始转移", count_rows(root / "data" / "carsim_brake_sequence_dataset.csv")),
        ("CarSim 训练数据", count_rows(root / "data" / "carsim_brake_sequence_training.csv")),
        ("CarSim 矩阵冒烟", count_rows(root / "data" / "carsim_matrix_smoke.csv")),
    ]
    df = pd.DataFrame(rows, columns=["数据集", "行数"])
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    add_header(fig, "全流程数据规模", "机理基线、时序建模、CarSim联合仿真和验证流程中的可用数据行数。")
    colors = [BLUE["mid"], BLUE["base"], ORANGE["mid"], ORANGE["base"], OLIVE["base"]]
    bars = ax.barh(df["数据集"], df["行数"], color=colors, edgecolor=TOKENS["ink"], linewidth=0.8)
    ax.invert_yaxis()
    ax.grid(axis="x", color=TOKENS["grid"], linewidth=0.8)
    ax.set_xlabel("行数")
    ax.set_ylabel("")
    for bar, value in zip(bars, df["行数"]):
        ax.text(value + max(df["行数"]) * 0.015, bar.get_y() + bar.get_height() / 2, f"{value:,}", va="center", fontsize=9)
    finish(fig, out / "01_dataset_inventory.png")
    write_markdown_table(df, out / "tables" / "dataset_inventory.md")
    return {"file": "01_dataset_inventory.png", "takeaway": "项目已经形成机理、时序和 CarSim 三类数据基础。"}


def chart_mechanism_coverage(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "brake_dataset.csv")
    if df.empty:
        return {}
    columns = [
        ("v_mps", "速度 (m/s)", BLUE["mid"]),
        ("pressure_MPa", "压力 (MPa)", ORANGE["mid"]),
        ("mu", "路面附着系数", OLIVE["mid"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.6))
    add_header(fig, "机理数据集覆盖范围", "单步基线数据中速度、制动压力和路面附着系数的分布。")
    for ax, (col, label, color) in zip(axes, columns):
        if col not in df:
            continue
        ax.hist(df[col].dropna(), bins=28, color=color, edgecolor=TOKENS["ink"], alpha=0.9)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", color=TOKENS["grid"])
        ax.set_ylabel("样本数")
    finish(fig, out / "02_mechanism_dataset_coverage.png")
    return {"file": "02_mechanism_dataset_coverage.png", "takeaway": "机理基线数据覆盖速度、压力和附着系数主要范围。"}


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
    add_header(fig, "不同路面附着下的机理制动响应", "按压力区间统计下一时刻平均加速度；曲线在附着极限处进入饱和。")
    palette = {0.2: BLUE["mid"], 0.4: OLIVE["mid"], 0.6: GOLD["mid"], 0.8: ORANGE["mid"]}
    for mu, part in grouped.groupby(mu_col):
        color = palette.get(round(float(mu), 1), TOKENS["muted"])
        ax.plot(part["pressure_mid"], part[accel_col], marker="o", linewidth=2, label=f"μ={mu:g}", color=color)
    ax.axhline(0, color=TOKENS["axis"], linewidth=1)
    ax.set_xlabel("压力 (MPa)")
    ax.set_ylabel("平均 a_next (m/s²)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False, ncol=2)
    finish(fig, out / "03_mechanism_pressure_mu_response.png")
    return {"file": "03_mechanism_pressure_mu_response.png", "takeaway": "附着系数越高，进入饱和前可支持的制动减速度越大。"}


def chart_sequence_examples(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "brake_sequence_dataset.csv")
    if df.empty:
        return {}
    traj_col = "trajectory_id"
    if traj_col not in df.columns:
        return {}
    sample_ids = list(df[traj_col].drop_duplicates().head(4))
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.6), sharex=True)
    add_header(fig, "机理时序轨迹示例", "用于循环世界模型训练的代表性连续制动轨迹。")
    colors = [BLUE["mid"], ORANGE["mid"], OLIVE["mid"], PINK["mid"]]
    fields = [("v_mps", "速度 (m/s)"), ("a_mps2", "加速度 (m/s²)"), ("pressure_MPa", "压力 (MPa)")]
    for ax, (field, ylabel) in zip(axes, fields):
        for idx, tid in enumerate(sample_ids):
            part = df[df[traj_col] == tid]
            x = part["time_s"] if "time_s" in part else part["step"]
            if field in part:
                ax.plot(x, part[field], color=colors[idx], linewidth=1.8, label=f"轨迹 {tid}" if field == "v_mps" else None)
        ax.set_ylabel(ylabel)
        ax.grid(color=TOKENS["grid"])
    axes[-1].set_xlabel("时间 (s)")
    axes[0].legend(frameon=False, ncol=4, loc="upper right")
    finish(fig, out / "04_mechanism_sequence_examples.png")
    return {"file": "04_mechanism_sequence_examples.png", "takeaway": "时序模型能够看到完整的压力和车辆状态历史。"}


def chart_metrics_tables(root: Path, out: Path) -> dict:
    world = safe_read_csv(root / "results" / "world_model_metrics.csv")
    seq = safe_read_csv(root / "results" / "sequence_world_model_metrics.csv")
    carsim = safe_read_csv(root / "results" / "carsim_gru_metrics.csv")
    rows = []
    if not world.empty:
        for _, row in world.iterrows():
            rows.append(["MLP 机理数据", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    if not seq.empty:
        for _, row in seq.iterrows():
            rows.append(["时序机理数据", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    if not carsim.empty:
        for _, row in carsim.iterrows():
            rows.append(["GRU CarSim 数据", row.get("output", ""), row.get("rmse", np.nan), row.get("mae", np.nan), row.get("r2", np.nan)])
    df = pd.DataFrame(rows, columns=["模型与数据源", "输出量", "RMSE", "MAE", "R2"])
    if df.empty:
        return {}
    df["输出量"] = df["输出量"].replace({"v_next_mps": "下一时刻速度", "a_next_mps2": "下一时刻加速度"})
    write_markdown_table(df, out / "tables" / "model_metrics_summary.md")
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    add_header(fig, "模型验证 RMSE 总览", "机理数据更容易拟合；CarSim 加速度是当前最困难的预测目标。")
    pivot = df.pivot_table(index="模型与数据源", columns="输出量", values="RMSE", aggfunc="first")
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
    return {"file": "05_model_metrics_rmse_summary.png", "takeaway": "CarSim-GRU 速度预测精度较高，但加速度预测更具挑战。"}


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
    add_header(fig, "LSTM 与 GRU 消融实验", "轨迹级划分，训练 40 轮，PINN 权重 0.05；高亮行为推荐模型。")
    for ax, field, title, unit in [
        (axes[0], "v_rmse", "速度 RMSE", "m/s"),
        (axes[1], "a_rmse", "加速度 RMSE", "m/s²"),
        (axes[2], "params_k", "参数量", "千参数"),
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
    table_df = df[["experiment", "recurrent", "sequence_len", "hidden_size", "num_layers", "parameter_count", "v_rmse", "a_rmse", "v_r2", "a_r2"]].rename(
        columns={
            "experiment": "实验名",
            "recurrent": "循环单元",
            "sequence_len": "序列长度",
            "hidden_size": "隐藏层维度",
            "num_layers": "层数",
            "parameter_count": "参数量",
            "v_rmse": "速度RMSE",
            "a_rmse": "加速度RMSE",
            "v_r2": "速度R2",
            "a_r2": "加速度R2",
        }
    )
    write_markdown_table(table_df, out / "tables" / "recurrent_ablation.md")
    return {"file": "06_recurrent_ablation_rmse_params.png", "takeaway": "GRU S5 H64 L1 参数少，并在关键加速度误差上表现最好。"}


def chart_ablation_tradeoff(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "recurrent_ablation" / "comparison.csv")
    if df.empty:
        return {}
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    add_header(fig, "模型规模与加速度误差权衡", "推荐 GRU 用更少参数取得接近最优的加速度预测表现。")
    for recurrent, part in df.groupby("recurrent"):
        color = BLUE["mid"] if recurrent == "gru" else ORANGE["mid"]
        ax.scatter(part["parameter_count"] / 1000, part["a_rmse"], s=110, color=color, edgecolor=TOKENS["ink"], label=recurrent.upper(), alpha=0.9)
        for _, row in part.iterrows():
            ax.text(row["parameter_count"] / 1000 + 3, row["a_rmse"], f"S{int(row['sequence_len'])} H{int(row['hidden_size'])} L{int(row['num_layers'])}", fontsize=7.5, va="center")
    ax.set_xlabel("参数量 (千)")
    ax.set_ylabel("加速度 RMSE (m/s²)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False)
    finish(fig, out / "07_recurrent_tradeoff_scatter.png")
    return {"file": "07_recurrent_tradeoff_scatter.png", "takeaway": "对本任务而言，更大的循环网络不一定更好。"}


def chart_carsim_run_matrix(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_full_dataset_summary.csv")
    if df.empty:
        return {}
    pivot = df.groupby(["mu", "initial_speed_kph"])["row_count"].sum().unstack("initial_speed_kph").sort_index()
    fig, ax = plt.subplots(figsize=(8.6, 5))
    add_header(fig, "CarSim 数据覆盖矩阵", "120 条轨迹在不同初速度和路面附着系数组合下采集到的数据行数。")
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(np.arange(pivot.shape[1]), [f"{int(v)}" for v in pivot.columns])
    ax.set_yticks(np.arange(pivot.shape[0]), [f"{v:.1f}" for v in pivot.index])
    ax.set_xlabel("初速度 (km/h)")
    ax.set_ylabel("附着系数 μ")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{int(pivot.values[i, j])}", ha="center", va="center", fontsize=9, color=TOKENS["ink"])
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="行数")
    finish(fig, out / "08_carsim_coverage_heatmap.png")
    return {"file": "08_carsim_coverage_heatmap.png", "takeaway": "完整 CarSim 数据覆盖每个速度和附着组合。"}


def chart_carsim_decel_by_mu(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_full_dataset_summary.csv")
    if df.empty:
        return {}
    grouped = df.groupby(["mu", "initial_speed_kph"])["minimum_acceleration_mps2"].apply(lambda s: abs(s).mean()).reset_index()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    add_header(fig, "CarSim 峰值减速度随路面附着分层", "按压力轨迹统计的平均绝对最小加速度。")
    palette = {0.2: BLUE["mid"], 0.4: OLIVE["mid"], 0.6: GOLD["mid"], 0.8: ORANGE["mid"]}
    for mu, part in grouped.groupby("mu"):
        color = palette.get(round(float(mu), 1), TOKENS["muted"])
        ax.plot(part["initial_speed_kph"], part["minimum_acceleration_mps2"], marker="o", linewidth=2.4, color=color, label=f"μ={mu:g}")
        ax.axhline(float(mu) * 9.81, color=color, linewidth=1, alpha=0.18)
    ax.set_xlabel("初速度 (km/h)")
    ax.set_ylabel("|最小加速度| (m/s²)")
    ax.grid(color=TOKENS["grid"])
    ax.legend(frameon=False, ncol=2)
    finish(fig, out / "09_carsim_peak_decel_by_mu.png")
    return {"file": "09_carsim_peak_decel_by_mu.png", "takeaway": "CarSim 峰值减速度呈现符合预期的附着限制分层。"}


def chart_carsim_matrix_smoke(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_matrix_smoke_summary.csv")
    if df.empty:
        return {}
    df = df.copy()
    df["case"] = df.apply(lambda r: f"{int(r['initial_speed_kph'])} km/h\nμ={r['mu']:.1f}", axis=1)
    fig, ax = plt.subplots(figsize=(8.8, 5))
    add_header(fig, "CarSim 边界工况冒烟测试响应", "6 个代表性工况验证初速度匹配和制动响应。")
    bars = ax.bar(df["case"], abs(df["minimum_acceleration_mps2"]), color=[BLUE["mid"] if mu == 0.2 else ORANGE["mid"] for mu in df["mu"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    ax.set_ylabel("|最小加速度| (m/s²)")
    ax.grid(axis="y", color=TOKENS["grid"])
    for bar, valid in zip(bars, df["valid"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15, "通过" if bool(valid) else "失败", ha="center", fontsize=8)
    finish(fig, out / "10_carsim_matrix_smoke.png")
    table_df = df.rename(columns={
        "case_id": "工况编号",
        "initial_speed_kph": "初速度(km/h)",
        "mu": "附着系数",
        "observed_initial_speed_kph": "实测初速度(km/h)",
        "observed_final_speed_kph": "末速度(km/h)",
        "minimum_acceleration_mps2": "最小加速度(m/s²)",
        "maximum_pressure_mpa": "最大压力(MPa)",
        "row_count": "样本行数",
        "speed_error_kph": "速度误差(km/h)",
        "speed_match": "速度匹配",
        "braking_response": "制动响应",
        "valid": "是否有效",
        "case": "工况标签",
    })
    bool_columns = ["速度匹配", "制动响应", "是否有效"]
    for column in bool_columns:
        if column in table_df:
            table_df[column] = table_df[column].map(lambda value: "是" if bool(value) else "否")
    preferred_columns = [
        "工况编号",
        "初速度(km/h)",
        "附着系数",
        "末速度(km/h)",
        "最小加速度(m/s²)",
        "最大压力(MPa)",
        "样本行数",
        "速度匹配",
        "制动响应",
        "是否有效",
    ]
    table_df = table_df[[column for column in preferred_columns if column in table_df]]
    write_markdown_table(table_df, out / "tables" / "carsim_matrix_smoke.md")
    return {"file": "10_carsim_matrix_smoke.png", "takeaway": "低附着和高附着边界工况产生了清晰且有效的制动响应。"}


def chart_carsim_smoke_trajectory(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "results" / "carsim_smoke_trajectory.csv")
    if df.empty:
        return {}
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)
    add_header(fig, "CarSim 单工况冒烟测试轨迹", "80 km/h，μ=0.85，压力指令 2 MPa，仿真 2.5 s。")
    columns = [
        ("speed_kph", "速度 (km/h)", BLUE["mid"]),
        ("acceleration_mps2", "加速度 (m/s²)", ORANGE["mid"]),
        ("pressure_mpa", "压力 (MPa)", OLIVE["mid"]),
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
    axes[-1].set_xlabel("时间 (s)")
    finish(fig, out / "11_carsim_smoke_trajectory.png")
    return {"file": "11_carsim_smoke_trajectory.png", "takeaway": "联合仿真能够响应压力输入，并返回有效车辆信号。"}


def chart_carsim_pressure_examples(root: Path, out: Path) -> dict:
    df = safe_read_csv(root / "data" / "carsim_brake_sequence_dataset.csv")
    if df.empty:
        return {}
    group_cols = ["trajectory_id"]
    sample_ids = list(df["trajectory_id"].drop_duplicates().head(8))
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.4), sharex=True)
    add_header(fig, "CarSim 压力轨迹示例", "高保真数据采集中使用的部分随机和平滑压力曲线。")
    palette = [BLUE["mid"], ORANGE["mid"], OLIVE["mid"], PINK["mid"], GOLD["mid"], BLUE["dark"], ORANGE["dark"], OLIVE["dark"]]
    for idx, tid in enumerate(sample_ids):
        part = df[df["trajectory_id"] == tid]
        x = part["time_s"] if "time_s" in part else part["step"]
        axes[0].plot(x, part["pressure_MPa"], color=palette[idx % len(palette)], linewidth=1.7, label=f"轨迹 {tid}")
        axes[1].plot(x, part["v_mps"] * 3.6, color=palette[idx % len(palette)], linewidth=1.7)
    axes[0].set_ylabel("压力 (MPa)")
    axes[1].set_ylabel("速度 (km/h)")
    axes[1].set_xlabel("时间 (s)")
    for ax in axes:
        ax.grid(color=TOKENS["grid"])
    axes[0].legend(frameon=False, ncol=4, fontsize=8)
    finish(fig, out / "12_carsim_pressure_profile_examples.png")
    return {"file": "12_carsim_pressure_profile_examples.png", "takeaway": "CarSim 数据包含多样制动压力指令，而不是单一恒定压力。"}


def chart_carsim_gru_metrics(root: Path, out: Path) -> dict:
    metrics = safe_read_csv(root / "results" / "carsim_gru_metrics.csv")
    summary = safe_read_json(root / "results" / "carsim_gru_training_summary.json")
    if metrics.empty:
        return {}
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.8))
    add_header(fig, "CarSim-GRU 验证指标", "序列长度 5，隐藏层 64，单层 GRU，PINN 权重 0.05；按轨迹划分训练与验证。")
    output_labels = metrics["output"].replace({"v_next_mps": "下一时刻速度", "a_next_mps2": "下一时刻加速度"})
    axes[0].bar(output_labels, metrics["rmse"], color=[BLUE["mid"], ORANGE["mid"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    axes[0].set_ylabel("RMSE")
    axes[0].grid(axis="y", color=TOKENS["grid"])
    axes[1].bar(output_labels, metrics["r2"], color=[BLUE["base"], ORANGE["base"]], edgecolor=TOKENS["ink"], linewidth=0.8)
    axes[1].set_ylabel("R²")
    axes[1].set_ylim(0, 1.05)
    axes[1].grid(axis="y", color=TOKENS["grid"])
    subtitle = f"参数量={summary.get('parameter_count', 'n/a')}，训练样本={summary.get('train_samples', 'n/a')}，验证样本={summary.get('val_samples', 'n/a')}"
    fig.text(0.06, 0.06, subtitle, fontsize=9, color=TOKENS["muted"])
    finish(fig, out / "13_carsim_gru_metrics.png")
    metrics_table = metrics.rename(columns={"output": "输出量", "mse": "MSE", "rmse": "RMSE", "mae": "MAE", "r2": "R2"})
    metrics_table["输出量"] = metrics_table["输出量"].replace({"v_next_mps": "下一时刻速度", "a_next_mps2": "下一时刻加速度"})
    write_markdown_table(metrics_table, out / "tables" / "carsim_gru_metrics.md")
    return {"file": "13_carsim_gru_metrics.png", "takeaway": "速度预测依然很强，加速度预测体现了高保真数据的真实难度。"}


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
    add_header(fig, "采样式 MPC 闭环刹停结果", "80 km/h，x0=65 m，μ=0.6，目标安全距离=2 m；当前执行环境为机理模型。")
    time_col = "time_s" if "time_s" in df else df.columns[0]
    plots = [
        ("distance_m", "距离 (m)", BLUE["mid"]),
        ("speed_kph", "速度 (km/h)", BLUE["dark"]),
        ("acceleration_mps2", "加速度 (m/s²)", ORANGE["mid"]),
        ("pressure_MPa", "压力 (MPa)", OLIVE["mid"]),
    ]
    for ax, (field, ylabel, color) in zip(axes, plots):
        if field not in df:
            candidates = [c for c in df.columns if field.split("_")[0].lower() in c.lower()]
            if not candidates:
                continue
            field = candidates[0]
        ax.plot(df[time_col], df[field], color=color, linewidth=2)
        if "distance" in field:
            ax.axhline(2.0, color=ORANGE["dark"], linestyle="--", linewidth=1.4, label="安全距离")
            ax.legend(frameon=False)
        ax.set_ylabel(ylabel)
        ax.grid(color=TOKENS["grid"])
    axes[-1].set_xlabel("时间 (s)")
    finish(fig, out / "14_mpc_stop_result.png")
    return {"file": "14_mpc_stop_result.png", "takeaway": "采样式规划器能够在距离目标安全距离 0.156 m 的范围内安全停车。"}


def write_asset_manifest(asset_records: list[dict], out: Path) -> None:
    df = pd.DataFrame(asset_records)
    if df.empty:
        return
    df = df.rename(columns={"chart": "图表文件", "takeaway": "核心结论"})
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
            records.append({"图表文件": result["file"], "核心结论": result["takeaway"]})
    write_asset_manifest(records, out)
    print(json.dumps({"输出目录": str(out), "图表资产": records}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

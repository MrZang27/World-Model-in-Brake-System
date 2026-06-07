"""Update the project presentation with the latest CarSim and GRU results.

The script edits the existing PPTX package directly so the original visual
theme, layouts, animations, and speaker-note structure are preserved.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SLIDE_TEXT = {
    1: [
        "基于世界模型的",
        "一维纵向制动决策规划",
        "Simulink / CarSim 联合仿真  ·  GRU-PINN  ·  采样式 MPC",
        "三人课程项目汇报  |  约 15 分钟",
        "预测 · 规划 · 执行 · 反馈",
        "汇报人：同学 A  /  同学 B  /  同学 C（可替换姓名）",
    ],
    2: [
        "问题定义：从“拟合动力学”走向“预测式决策”",
        "PART 1 / 3",
        "目标：给定当前状态，在线选择制动压力，使车辆安全、精准、平顺地停在障碍物前。",
        "状态 State",
        "vₜ：当前车速\nxₜ：剩余距离\naₜ：当前减速度\nμₜ：路面附着系数",
        "动作 Action",
        "Pₜ：制动主缸压力\n\n控制范围：0–10 MPa\n滚动执行：每次只应用第一步",
        "目标 Objective",
        "安全：避免 x < 0\n精准：x_stop ≈ d_safe\n舒适：限制减速度与压力突变",
        "关键转变：",
        "世界模型不再只是“预测器”，而是规划器内部可快速试错的虚拟环境。",
        "汇报人 A  ·  建议用时 1:00",
        "02",
    ],
    3: [
        "当前工程闭环：机制基线 → CarSim 数据 → GRU 世界模型 → MPC",
        "PART 1 / 3",
        "① 双层仿真环境",
        "Simulink 机制基线\nCarSim 高保真整车",
        "② 统一数据集",
        "30,000 单步 + 16,000 时序\n13,070 CarSim 状态转移",
        "③ 世界模型",
        "MLP 基线\nLSTM / GRU + PINN",
        "④ 决策与验证",
        "24 Run 根验证\n采样式 MPC",
        "结果反馈、消融实验与数据迭代",
        "MATLAB 产物",
        "brake_mechanism_model.slx\ncarsim_brake_cosim.slx",
        "PyTorch 产物",
        "world_model_gru.pt\nLSTM / GRU 消融结果",
        "验证产物",
        "24 工况库 · 120 条轨迹\nGRU 指标 · MPC 刹停曲线",
        "统一接口：[vₜ, aₜ, Pₜ, μₜ]  →  [vₜ₊₁, aₜ₊₁]",
        "汇报人 A  ·  建议用时 1:20",
        "03",
    ],
    4: [
        "机制基线：先建立可解释的物理下限与统一数据接口",
        "PART 1 / 3",
        "纵向制动核心方程",
        "F_brake = k · P",
        "F_actual = min(F_brake, μmg)",
        "aₜ₊₁ = −F_actual / m",
        "vₜ₊₁ = max(vₜ + aₜ₊₁Δt, 0)",
        "m = 1800 kg   ·   Δt = 0.05 s\nk = 3500 N/MPa",
        "覆盖：20–120 km/h · 0–10 MPa · μ=0.2/0.4/0.6/0.8；用于单元测试、数据规范与 MPC fallback",
        "汇报人 A  ·  建议用时 1:20",
        "04",
    ],
    5: [
        "CarSim 联合仿真：24 个独立 Run 根与 120 条压力轨迹已跑通",
        "PART 2 / 3",
        "工况库验证",
        "6 速度 × 4 μ = 24 工况\nRun 根唯一性：24/24 PASS",
        "批量数据集",
        "每工况 5 条压力轨迹\n13,070 条状态转移",
        "边界响应",
        "低附着峰值约 2 m/s²\n高附着峰值约 7.3 m/s²",
        "CarSim 2019 + MATLAB R2024b；统一重采样 Δt = 0.05 s",
        "汇报人 B  ·  建议用时 1:20",
        "05",
    ],
    6: [
        "模型升级：GRU 捕捉历史依赖，PINN 保证运动学一致",
        "PART 2 / 3",
        "单步 MLP：机制基线",
        "当前点",
        "[vₜ, Pₜ, μₜ]",
        "下一点",
        "[vₜ₊₁, aₜ₊₁]",
        "适合验证数据链路；无法显式表达建压滞后与历史状态",
        "升级",
        "GRU：轻量序列建模",
        "t-4",
        "t-3",
        "t-2",
        "t-1",
        "t-0",
        "预测",
        "利用过去 K=5 步 [v, a, P, μ]，门控状态记忆压力建立过程",
        "PINN 约束：",
        "Loss = MSE_data + λ · [v̂ₜ₊₁ − max(vₜ + âₜ₊₁Δt, 0)]²",
        "汇报人 B  ·  建议用时 1:15",
        "06",
    ],
    7: [
        "消融实验：GRU 在短序列下以更少参数获得更低误差",
        "PART 2 / 3",
        "推荐配置",
        "1",
        "2",
        "3",
        "4",
        "5",
        "GRU 64",
        "FC + ReLU\nFC → 2",
        "输入：5 × [v, a, P, μ]\n参数：17,730",
        "速度 RMSE",
        "GRU 0.0648 vs LSTM 0.0803（↓19.2%）",
        "减速度 RMSE",
        "GRU 0.0431 vs LSTM 0.1450（↓70.3%）",
        "参数量",
        "17,730 vs 22,210（↓20.2%）",
        "汇报人 B  ·  建议用时 1:30",
        "07",
    ],
    8: [
        "CarSim-GRU 结果：在更真实、更难的数据上保持可用精度",
        "PART 2 / 3",
        "高保真数据源",
        "CarSim 2019 / S-Function\n轮胎非线性 · 俯仰 · 轮速",
        "统一 CSV",
        "共享接口",
        "trajectory / step\n[v, a, P, μ] → next state",
        "直接训练",
        "推荐模型",
        "GRU-PINN\nS=5 · H=64 · L=1",
        "数据覆盖",
        "初速度",
        "20–120 km/h",
        "主缸压力",
        "0–10 MPa",
        "附着系数",
        "0.2 / 0.4 / 0.6 / 0.8",
        "物理工况",
        "24",
        "压力轨迹",
        "120",
        "训练配置",
        "轨迹级划分 96 / 24\n40 epochs · CUDA 17.2 s\n有效序列 10,444",
        "验证指标",
        "v_next RMSE 0.1173 m/s\nR² 0.99981\n\na_next RMSE 0.4493 m/s²\nR² 0.92929",
        "汇报人 B  ·  建议用时 1:20",
        "08",
    ],
    9: [
        "上层世界模型规划：在“脑内”比较未来制动轨迹",
        "PART 3 / 3",
        "上层：采样式规划器",
        "状态 [vₜ, xₜ, μₜ]\n生成候选压力序列 U",
        "中层：学习世界模型",
        "GRU / PINN\n滚动预测未来轨迹",
        "下层：物理执行环境",
        "机制模型（当前闭环）\nCarSim（高保真数据与验证）",
        "状态反馈",
        "vₜ₊₁, aₜ₊₁, xₜ₊₁",
        "代价评估",
        "安全距离 · 舒适性\n压力平滑 · 碰撞惩罚",
        "滚动优化：只执行最优序列的第一步，再根据真实反馈重规划",
        "汇报人 C  ·  建议用时 1:10",
        "09",
    ],
    10: [
        "采样式 MPC：不求复杂梯度，直接预测并排序",
        "PART 3 / 3",
        "1",
        "采样动作",
        "生成约 256 条\n平滑压力序列",
        "2",
        "脑内演化",
        "GRU 世界模型滚动\n预测 N 步",
        "3",
        "计算代价",
        "安全、精准\n舒适、平滑",
        "4",
        "执行首步",
        "输出最优 Pₜ\n下一时刻重规划",
        "J = w_d (x_stop − d_safe)²  +  w_a mean(a²)  +  w_p mean(ΔP²)",
        "+ collision_penalty  +  not_stop_penalty",
        "候选压力曲线示意",
        "工程优势",
        "无需对网络求解析梯度；约束可直接写入代价；可继续升级到 MPPI / CEM。",
        "汇报人 C  ·  建议用时 1:15",
        "10",
    ],
    11: [
        "闭环刹停验证：当前机制执行环境下 80 km/h 安全停车",
        "PART 3 / 3",
        "实验工况",
        "v₀ = 80 km/h  ·  x₀ = 65 m\nμ = 0.6  ·  d_safe = 2 m",
        "刹停结果",
        "停止时间  5.05 s\n最终距离  1.844 m",
        "目标误差",
        "|1.844 − 2.000| = 0.156 m\n无碰撞，速度降至 0",
        "仍可优化",
        "后段减速度约 −5.72 m/s²\n下一步接入 CarSim 在线执行",
        "汇报人 C  ·  建议用时 1:30",
        "11",
    ],
    12: [
        "总结：高保真数据、轻量世界模型与滚动规划已形成工程闭环",
        "PART 3 / 3",
        "① 数据闭环",
        "机制模型 + CarSim 联合仿真\n24 物理工况 · 120 条轨迹\n13,070 条状态转移",
        "② 模型底座",
        "MLP 基线\nLSTM / GRU-PINN 消融\nCarSim-GRU 完成训练",
        "③ 决策规划",
        "采样式 MPC 滚动优化\n80 km/h 工况安全刹停\n最终距离误差 0.156 m",
        "下一阶段路线",
        "在线闭环",
        "CarSim 实时执行",
        "泛化验证",
        "μ 突变 / 噪声 / 热衰退",
        "控制升级",
        "MPPI / CEM",
        "部署评估",
        "时延与鲁棒性",
        "核心结论：",
        "关键不是单个网络精度，而是“高保真环境—可学习模型—在线规划—反馈验证”的完整闭环。",
        "A：环境与 CarSim 数据  ·  B：GRU 消融与训练  ·  C：MPC、结果分析与统筹",
        "汇报人 C  ·  建议用时 1:10",
        "12",
    ],
}


NOTES = {
    1: (
        "【建议用时 40 秒｜同学 A】各位老师、同学好，我们汇报的题目是“基于世界模型的一维纵向制动决策规划”。"
        "项目最初从简化的 Simulink 纵向制动模型出发，现在已经扩展到 CarSim 与 Simulink 联合仿真、GRU-PINN 时序世界模型，"
        "并用采样式 MPC 完成一维刹停决策。我们希望展示的不只是一个预测网络，而是一条从高保真数据、模型训练到滚动规划和反馈验证的完整工程链路。"
        "接下来三位同学分别介绍环境与数据、模型升级，以及上层规划与结果。"
    ),
    2: (
        "【建议用时 1 分钟｜同学 A】我们的核心问题不是单纯预测下一时刻速度，而是让预测真正参与制动决策。场景限定为一维直线刹停："
        "已知当前车速、与障碍物的剩余距离、当前减速度和路面附着系数，控制量是零到十兆帕的制动主缸压力。系统同时追求三个目标："
        "首先不能碰撞；其次希望停车后距离障碍物约两米；最后要限制过大的减速度和压力突变。控制采用滚动方式，每次规划一段未来压力曲线，"
        "但只执行第一步，再利用新反馈重新计算。由此，世界模型从离线拟合器变成了规划器内部能够快速试错的虚拟环境。"
    ),
    3: (
        "【建议用时 1 分 20 秒｜同学 A】这张图概括当前已经跑通的工程闭环。第一层是仿真环境：简化机制模型负责快速调试和物理基线，"
        "CarSim 负责提供包含轮胎和整车动态的高保真数据。第二层是统一数据接口，我们保留了原来的三万条单步样本和一万六千行时序样本，"
        "并新增一万三千零七十条 CarSim 状态转移。第三层是世界模型：先用 MLP 验证单步链路，再系统比较 LSTM 和 GRU，并加入运动学残差。"
        "第四层是验证和决策：二十四个独立 CarSim Run 根全部通过检查，上层采用采样式 MPC。所有环节都有可复现的模型、脚本、CSV、权重和指标文件，"
        "因此这已经是一条可持续迭代的工程管线，而不只是概念示意图。"
    ),
    4: (
        "【建议用时 1 分 20 秒｜同学 A】在没有实车数据时，我们先保留一个可解释的机制基线。制动力与主缸压力近似线性，但不能超过路面最大附着力 μmg，"
        "因此实际制动力取两者较小值，再通过牛顿第二定律和离散积分更新减速度与速度。车辆质量设为一千八百千克，采样周期是零点零五秒。"
        "图中可以看到，同样的制动压力在不同附着系数下会出现明显不同的减速度上限。这个模型的价值有三点：第一，能够快速生成和检查数据格式；"
        "第二，作为单元测试的物理参考；第三，在规划调试阶段作为稳定的执行环境和 fallback。它不会被当成高保真真值，复杂动力学由后面的 CarSim 补充。"
        "下面交给同学 B 介绍联合仿真和学习模型。"
    ),
    5: (
        "【建议用时 1 分 20 秒｜同学 B】CarSim 联合仿真已经从模板阶段进入批量可用阶段。我们按六档初速度，也就是二十到一百二十公里每小时，"
        "以及四档附着系数零点二到零点八，建立了二十四个相互独立的 Run 根。验证脚本检查了文件数量、根标识唯一性、速度和附着条件，二十四项全部通过。"
        "每个物理工况再施加五条不同压力轨迹，总计一百二十条轨迹和一万三千零七十条状态转移。左图显示 CarSim 的峰值减速度会随附着系数形成清晰分层："
        "低附着约为二米每二次方秒，高附着约为七点三米每二次方秒，符合附着极限。单工况和六个边界工况的烟雾测试也全部通过，说明 SIMFILE 切换、压力输入、"
        "信号输出和重采样链路已经稳定。"
    ),
    6: (
        "【建议用时 1 分 15 秒｜同学 B】单步 MLP 能验证数据生成、归一化和推理链路，但它只看到当前一个点，难以表达液压建压、执行器滞后和轮胎状态的历史影响。"
        "因此我们把输入改为过去五个时间步的速度、减速度、压力和附着系数序列，并把循环单元升级为 GRU。GRU 相比 LSTM 门结构更少，参数更紧凑，"
        "适合后续在 MPC 中反复调用。除了数据均方误差，我们还加入 PINN 形式的运动学残差，要求网络预测的下一时刻速度与当前速度、预测减速度和采样周期之间基本一致。"
        "这个约束不是替代数据，而是减少违反基本运动学的预测，尤其有助于小数据和分布外工况的稳定性。"
    ),
    7: (
        "【建议用时 1 分 30 秒｜同学 B】为了避免凭经验挑网络，我们做了一个完整消融实验。LSTM 和 GRU 各测试四组配置：序列长度五或五十，"
        "隐藏维度六十四或一百二十八，以及单层或双层，所有实验使用相同的轨迹级划分、随机种子、四十轮训练和物理损失权重。图中比较速度 RMSE、减速度 RMSE 和参数量。"
        "推荐的 GRU 短序列单层模型只有一万七千七百三十个参数，比同配置 LSTM 少百分之二十点二；速度 RMSE 从零点零八零三降到零点零六四八，下降百分之十九点二；"
        "减速度 RMSE 从零点一四五零降到零点零四三一，下降百分之七十点三。长序列深模型虽然在个别速度指标上更好，但参数量约增加九倍，减速度误差也没有同步改善。"
        "因此我们选择短序列、六十四隐藏单元、单层 GRU，兼顾精度、速度和规划调用成本。"
    ),
    8: (
        "【建议用时 1 分 20 秒｜同学 B】选定结构后，我们直接使用 CarSim 数据训练同一套 GRU-PINN。数据按照完整轨迹划分，而不是随机打散相邻时间点，"
        "训练集九十六条轨迹，验证集二十四条轨迹，最终形成一万零四百四十四个有效序列。模型训练四十轮，GPU 用时约十七点二秒。"
        "验证集上，下一时刻速度 RMSE 为零点一一七三米每秒，R 方为零点九九九八一；减速度 RMSE 为零点四四九三米每二次方秒，R 方为零点九二九二九。"
        "相比简化机制数据，CarSim 的减速度误差明显更高，这是合理且更诚实的结果，因为数据包含更复杂的轮胎、俯仰和停车附近非线性。"
        "当前精度已经能够支撑短时预测实验，同时也指出后续应重点处理低速停车段、滑移状态和更多历史变量。下面交给同学 C。"
    ),
    9: (
        "【建议用时 1 分 10 秒｜同学 C】世界模型的真正价值是让规划器能够在很短时间内比较大量未来。上层读取当前速度、剩余距离和附着系数，"
        "生成多条候选压力序列；中层 GRU-PINN 对每条序列展开未来速度和减速度；根据距离、舒适性和平滑性计算代价后，只把最优序列的第一步压力交给物理环境。"
        "得到下一时刻反馈以后，再重复整个过程，这就是滚动时域优化。这里需要准确区分两类验证：CarSim 已经用于高保真数据采集、边界工况验证和 GRU 训练；"
        "当前展示的完整刹停闭环仍由机制模型执行。这样的分层让我们可以先验证规划逻辑，再把下层逐步替换为 CarSim 在线执行。"
    ),
    10: (
        "【建议用时 1 分 15 秒｜同学 C】我们采用采样式 MPC，主要考虑实现透明、约束容易加入，而且不要求对神经网络推导解析梯度。每个控制时刻生成约二百五十六条"
        "平滑压力曲线，并加入恒压、渐增和渐减等确定性候选。世界模型对每条曲线滚动预测 N 步，代价函数包括停车位置与安全距离的平方误差、平均减速度平方、"
        "压力变化平方，以及碰撞和预测时域内未停车的惩罚。选出代价最低的序列后只执行第一个压力值，下一时刻重新采样。这种方案目前是随机搜索，"
        "但数据接口和代价函数都可以直接保留，后续只需要把采样器升级为 MPPI 或 CEM，就能提高搜索效率。"
    ),
    11: (
        "【建议用时 1 分 30 秒｜同学 C】这里展示当前机制执行环境下的完整闭环刹停结果。初始速度八十公里每小时，障碍物初始距离六十五米，"
        "附着系数零点六，目标安全距离两米。规划器前半段采用较温和的压力，随后根据剩余距离提高制动强度，车辆在五点零五秒停止。最终距离为一点八四四米，"
        "与目标相差零点一五六米，没有碰撞。四幅曲线分别给出距离、速度、减速度和压力，可以看到控制并不是固定压力，而是在反馈下动态调整。"
        "需要说明，这张图验证的是世界模型参与规划和滚动执行的算法闭环，物理执行端目前仍是机制模型，不把它表述为 CarSim 在线 MPC 结果。"
        "后段减速度约负五点七二米每二次方秒，压力也存在阶跃，下一步会通过提高舒适度和平滑项权重，并接入 CarSim 在线执行进一步验证。"
    ),
    12: (
        "【建议用时 1 分 10 秒｜同学 C】最后总结。数据层已经形成机制模型与 CarSim 双环境，二十四个物理工况、一百二十条压力轨迹和一万三千零七十条状态转移均已落盘。"
        "模型层完成了 MLP 基线、LSTM 与 GRU 的统一消融，并训练出面向 CarSim 数据的轻量 GRU-PINN。规划层实现了采样式 MPC，在八十公里每小时工况下完成安全刹停，"
        "终点误差约零点一五六米。下一阶段重点是让 CarSim 成为在线执行环境，增加附着系数突变、噪声和制动热衰退等场景，并升级 MPPI 或 CEM，同时评估实时延迟和鲁棒性。"
        "我们的核心结论是：世界模型项目的价值不只在单个网络精度，而在于高保真环境、可学习模型、在线规划和反馈验证能否构成可复现的闭环。谢谢大家。"
    ),
}


TEXT_PATTERN = re.compile(rb"(<a:t(?:\s[^>]*)?>)(.*?)(</a:t>)", re.DOTALL)


def replace_text_nodes(xml_bytes: bytes, texts: list[str], part_name: str) -> bytes:
    matches = list(TEXT_PATTERN.finditer(xml_bytes))
    if len(matches) != len(texts):
        raise RuntimeError(
            f"{part_name}: expected {len(texts)} text nodes, found {len(matches)}"
        )

    chunks: list[bytes] = []
    cursor = 0
    for match, text in zip(matches, texts, strict=True):
        chunks.append(xml_bytes[cursor : match.start(2)])
        chunks.append(html.escape(text, quote=False).encode("utf-8"))
        cursor = match.end(2)
    chunks.append(xml_bytes[cursor:])
    return b"".join(chunks)


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Microsoft YaHei",
                "SimHei",
                "Arial Unicode MS",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "axes.edgecolor": "#334155",
            "axes.labelcolor": "#334155",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
            "text.color": "#0F172A",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def build_carsim_chart(project_root: Path, output_path: Path) -> None:
    summary_path = project_root / "results" / "carsim_full_dataset_summary.csv"
    grouped: dict[tuple[float, float], list[float]] = {}
    with summary_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key = (float(row["mu"]), float(row["initial_speed_kph"]))
            grouped.setdefault(key, []).append(
                abs(float(row["minimum_acceleration_mps2"]))
            )

    speeds = sorted({key[1] for key in grouped})
    mus = sorted({key[0] for key in grouped})
    colors = ["#0F766E", "#2563EB", "#D97706", "#DC2626"]

    fig, ax = plt.subplots(figsize=(8.4, 5.8), dpi=160)
    for mu, color in zip(mus, colors, strict=True):
        values = [np.mean(grouped[(mu, speed)]) for speed in speeds]
        ax.plot(
            speeds,
            values,
            marker="o",
            linewidth=2.6,
            markersize=5.5,
            color=color,
            label=f"μ = {mu:.1f}",
        )
        ax.axhline(mu * 9.81, color=color, linewidth=1.0, alpha=0.18)

    ax.set_title("CarSim 工况矩阵：峰值减速度随附着系数分层", fontsize=14, pad=12)
    ax.set_xlabel("初速度 (km/h)")
    ax.set_ylabel("|最小纵向加速度| (m/s²)")
    ax.set_xticks(speeds)
    ax.set_ylim(0, 8.4)
    ax.grid(True, alpha=0.22)
    ax.legend(ncol=2, frameon=False, loc="upper left")
    fig.text(
        0.5,
        0.018,
        "24 物理工况 × 5 压力轨迹 = 120 条轨迹；所有 Run 根与边界响应验证通过",
        ha="center",
        fontsize=9.5,
        color="#475569",
    )
    fig.tight_layout(rect=(0.02, 0.055, 0.98, 0.98))
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def build_ablation_chart(project_root: Path, output_path: Path) -> None:
    comparison_path = project_root / "results" / "recurrent_ablation" / "comparison.csv"
    rows: list[dict[str, str]] = []
    with comparison_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows.extend(csv.DictReader(file))

    labels = []
    speed_rmse = []
    accel_rmse = []
    parameters = []
    colors = []
    for row in rows:
        recurrent = row["recurrent"].upper()
        labels.append(
            f"{recurrent} S{row['sequence_len']} H{row['hidden_size']} L{row['num_layers']}"
        )
        speed_rmse.append(float(row["v_rmse"]))
        accel_rmse.append(float(row["a_rmse"]))
        parameters.append(float(row["parameter_count"]) / 1000.0)
        is_recommended = row["experiment"] == "gru_s5_h64_l1"
        colors.append("#0F766E" if is_recommended else ("#5EA8A2" if recurrent == "GRU" else "#F59E72"))

    y = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 6.6), dpi=160, sharey=True)
    metrics = [
        (speed_rmse, "速度 RMSE", "m/s"),
        (accel_rmse, "减速度 RMSE", "m/s²"),
        (parameters, "参数量", "千参数"),
    ]
    for ax, (values, title, unit) in zip(axes, metrics, strict=True):
        bars = ax.barh(y, values, color=colors, height=0.66)
        ax.set_title(title, fontsize=13, pad=10)
        ax.set_xlabel(unit)
        ax.grid(axis="x", alpha=0.2)
        ax.invert_yaxis()
        maximum = max(values)
        ax.set_xlim(0, maximum * 1.24)
        for bar, value in zip(bars, values, strict=True):
            fmt = f"{value:.3f}" if maximum < 1 else f"{value:.1f}"
            ax.text(
                value + maximum * 0.018,
                bar.get_y() + bar.get_height() / 2,
                fmt,
                va="center",
                fontsize=8,
            )

    axes[0].set_yticks(y, labels=labels, fontsize=8.5)
    for ax in axes[1:]:
        ax.tick_params(axis="y", labelleft=False)
    fig.suptitle("LSTM / GRU 消融实验（轨迹级划分，40 epochs）", fontsize=15, y=0.98)
    fig.text(
        0.5,
        0.012,
        "深绿色为推荐配置：GRU S5 H64 L1，兼顾误差、参数量与 MPC 推理成本",
        ha="center",
        fontsize=9.5,
        color="#475569",
    )
    fig.tight_layout(rect=(0.02, 0.045, 0.99, 0.94), w_pad=1.3)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def update_presentation(input_path: Path, output_path: Path, project_root: Path) -> dict:
    configure_plot_style()
    with tempfile.TemporaryDirectory(prefix="world_model_ppt_") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        carsim_chart = temp_dir / "image2.png"
        ablation_chart = temp_dir / "image3.png"
        build_carsim_chart(project_root, carsim_chart)
        build_ablation_chart(project_root, ablation_chart)

        with zipfile.ZipFile(input_path, "r") as source:
            members = {name: source.read(name) for name in source.namelist()}

        for slide_index, texts in SLIDE_TEXT.items():
            name = f"ppt/slides/slide{slide_index}.xml"
            members[name] = replace_text_nodes(members[name], texts, name)

        for slide_index, note in NOTES.items():
            name = f"ppt/notesSlides/notesSlide{slide_index}.xml"
            members[name] = replace_text_nodes(members[name], [note], name)

        members["ppt/media/image2.png"] = carsim_chart.read_bytes()
        members["ppt/media/image3.png"] = ablation_chart.read_bytes()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_output = output_path.with_suffix(".tmp.pptx")
        with zipfile.ZipFile(
            temporary_output, "w", compression=zipfile.ZIP_DEFLATED
        ) as destination:
            for name, payload in members.items():
                destination.writestr(name, payload)
        temporary_output.replace(output_path)

    total_seconds = 40 + 60 + 80 + 80 + 80 + 75 + 90 + 80 + 70 + 75 + 90 + 70
    return {
        "output": str(output_path),
        "slides": len(SLIDE_TEXT),
        "notes": len(NOTES),
        "duration_seconds": total_seconds,
        "duration_display": f"{total_seconds // 60}:{total_seconds % 60:02d}",
        "images_replaced": ["ppt/media/image2.png", "ppt/media/image3.png"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/World_Model_Brake_System_12min_3speakers.pptx"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    input_path = args.input
    if not input_path.is_absolute():
        input_path = project_root / input_path
    output_path = args.output or input_path
    if not output_path.is_absolute():
        output_path = project_root / output_path

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if output_path.resolve() == input_path.resolve() and not args.no_backup:
        backup_path = input_path.with_name(
            "World_Model_Brake_System_12min_3speakers.backup.pptx"
        )
        if not backup_path.exists():
            shutil.copy2(input_path, backup_path)

    result = update_presentation(input_path, output_path, project_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

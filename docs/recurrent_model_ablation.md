# GRU/LSTM 消融实验说明

## 实验目的

本实验回答三个问题：

1. GRU 是否可以替代原来的单层 LSTM？
2. 增大隐层维度并堆叠两层循环网络是否有收益？
3. 将历史窗口从 5 步增加到 50 步是否有收益？

## 控制变量

除循环网络类型、序列长度、隐层宽度和层数外，其他条件保持一致：

```text
数据集：data/brake_sequence_dataset.csv
轨迹数：200
每条轨迹：80 步
训练/验证：160/40 条完整轨迹
epochs：40
batch size：256
PINN weight：0.05
seed：11
device：CUDA
```

实验采用按轨迹划分，而不是随机划分滑窗。因为相邻滑窗高度重叠，如果同一条轨迹
同时进入训练集和验证集，会形成数据泄漏并高估验证性能。

## 实验矩阵

对 LSTM 和 GRU 分别运行以下四组配置，共八组：

```powershell
# 配置 1：短序列、单层、小模型
--sequence-len 5 --hidden-size 64 --num-layers 1

# 配置 2：短序列、两层、大模型
--sequence-len 5 --hidden-size 128 --num-layers 2

# 配置 3：长序列、单层、小模型
--sequence-len 50 --hidden-size 64 --num-layers 1

# 配置 4：长序列、两层、大模型
--sequence-len 50 --hidden-size 128 --num-layers 2
```

一键复现实验：

```powershell
& "C:\Users\MrZang\anaconda3\condabin\conda.bat" run -n rl_env `
  python python/run_recurrent_ablation.py `
  --data data/brake_sequence_dataset.csv `
  --epochs 40 `
  --force
```

输出目录：

```text
results/recurrent_ablation/
```

详细数值见：

- `results/recurrent_ablation/comparison.csv`
- `results/recurrent_ablation/report.md`

## 结果解释

默认单层 GRU 是综合精度、参数量和训练效率最好的配置。与同规格 LSTM 相比：

```text
参数量：22,210 -> 17,730，减少 20.17%
速度 RMSE：0.080260 -> 0.064829，降低 19.23%
加速度 RMSE：0.145007 -> 0.043108，降低 70.27%
```

两层长序列 GRU 得到了最低的速度 RMSE，但其加速度预测和模型复杂度不占优势。
由于世界模型需要同时服务速度演化、舒适性代价和 MPC 多步滚动预测，不能只根据
速度指标选择模型，因此项目默认采用：

```text
GRU(sequence_len=5, hidden_size=64, num_layers=1)
```

## 科学性与限制

- 本轮实验只使用一个随机种子，因此可以比较配置，但尚不能给出统计显著性结论。
- 更严格的实验应使用至少 3-5 个随机种子，报告均值和标准差。
- 当前数据来自简化机理模型；完成 CarSim 数据采集后，应在 CarSim 数据上重复同一
  实验矩阵。
- 还应增加多步闭环误差和最终刹停误差，因为最低单步 RMSE 不一定意味着最优 MPC
  闭环性能。


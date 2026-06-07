# CarSim/Simulink 联合仿真验收

## 已验证环境

```text
CarSim: 2019.0
Vehicle configuration: I_S
Vehicle solver: F:\Carsim\Programs\solvers\carsim_64.dll
CarSim external step: 0.001 s
Simulink: MATLAB R2024b
Run initial speed: 80 km/h
Road mu: 0.85
Pressure command: 2 MPa
Simulation time: 2.5 s
```

## 冒烟测试结果

| 指标 | 结果 |
|---|---:|
| 原始样本数 | 2501 |
| 原始采样间隔 | 0.001 s |
| 初速度 | 80.000 km/h |
| 最终速度 | 58.373 km/h |
| 速度下降 | 21.627 km/h |
| 最小纵向加速度 | -3.238 m/s² |
| 最大压力 | 2.000 MPa |
| 有限数值检查 | 通过 |
| 速度单调下降 | 通过 |
| 速度差分与加速度平均误差 | 约 0.002 m/s² |
| 总体结果 | PASS |

## 结论

CarSim 64 位车辆求解器能够由 Simulink VehicleSim S-Function 正确加载。
四轮制动压力输入、`Vx_SM` 和 `Ax_SM` 输出、单位换算以及时间对齐均已通过
单工况验证。

## 正式数据采集器验收

`verify_carsim_dataset_smoke` 已使用同一 CarSim Run 和随机压力曲线完成验证：

| 指标 | 结果 |
|---|---:|
| transition 数量 | 50 |
| 轨迹数量 | 1 |
| 机器学习采样周期 | 0.050 s |
| 初速度 | 80.000 km/h |
| 最终速度 | 35.661 km/h |
| 最大随机压力 | 6.245 MPa |
| 最小纵向加速度 | -7.754 m/s² |
| transition 连续性最大误差 | 0 |
| 速度积分残差平均值 | 0.0062 m/s |
| 速度积分残差最大值 | 0.0262 m/s |
| NaN/Inf 检查 | 通过 |
| 数据来源字段 | CarSim |
| 总体结果 | PASS |

## GRU 数据接口验收

Python 数据加载器直接读取：

```text
data/carsim_dataset_smoke.csv
```

使用 `sequence_len=5` 成功生成：

```text
输入形状：(46, 5, 4)
标签形状：(46, 2)
输入字段：[v_mps, a_mps2, pressure_MPa, mu]
标签字段：[v_next_mps, a_next_mps2]
```

因此 CarSim 数据已经与当前 GRU/PINN 训练接口完全兼容。

## 多工况 Run 切换验收

24 个 `.sim` 文件已通过 Run 库验证：

```text
文件数量：24
独立 Run UUID：24
实际速度和 mu 匹配：24/24
```

进一步运行了 6 个边界工况：

| 初速度 | mu | 最终速度 | 最小加速度 | 结果 |
|---:|---:|---:|---:|---|
| 20 km/h | 0.2 | 1.386 km/h | -1.772 m/s² | PASS |
| 20 km/h | 0.8 | 0 km/h | -7.328 m/s² | PASS |
| 80 km/h | 0.2 | 61.102 km/h | -1.897 m/s² | PASS |
| 80 km/h | 0.8 | 9.603 km/h | -7.344 m/s² | PASS |
| 120 km/h | 0.2 | 99.631 km/h | -1.995 m/s² | PASS |
| 120 km/h | 0.8 | 53.834 km/h | -7.327 m/s² | PASS |

所有工况的实际初速度误差均接近 0。低附着路面的峰值减速度约为
`1.8-2.0 m/s²`，高附着路面约为 `7.3 m/s²`，说明 VehicleSim 已真实切换不同
路面工况，而不是仅修改数据标签。

## 剩余工作

24 个物理工况已经准备完毕。下一步运行 `run_carsim_full_collection` 生成
120 条随机压力轨迹，然后使用该数据重新训练和比较 GRU/LSTM。

## 完整 CarSim 数据集

完整批量采集已经通过：

```text
transitions:         13,070
trajectories:        120
physical conditions: 24
valid trajectories:  120/120
result:               PASS
```

数据覆盖：

```text
速度：0-120 km/h
压力：0-10 MPa
mu：0.2 / 0.4 / 0.6 / 0.8
```

停车后的 CarSim 车身回弹数据不适合作为一维刹停世界模型的持续运动标签。使用
`python/prepare_carsim_training_dataset.py` 截断停车后的样本并建立零速吸收状态：

```text
原始 transition：13,070
训练 transition：10,924
移除停车后样本：2,146
保留轨迹：120
保留物理工况：24
```

## CarSim-GRU 训练结果

使用以下配置训练：

```text
GRU
sequence_len=5
hidden_size=64
num_layers=1
epochs=40
PINN weight=0.05
trajectory-level split=96/24
```

结果：

| 输出 | RMSE | MAE | R² |
|---|---:|---:|---:|
| 下一时刻速度 | 0.1173 m/s | 0.0918 m/s | 0.99981 |
| 下一时刻加速度 | 0.4493 m/s² | 0.2016 m/s² | 0.92929 |

模型共有 17,730 个参数，CUDA 训练 40 轮约 17.2 秒。检查点已通过 MPC 加载验证。

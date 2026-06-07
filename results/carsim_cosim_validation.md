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

## 剩余工作

当前 `simfile.sim` 只代表一个真实 CarSim 工况：

```text
初速度：80 km/h
路面附着系数：0.85
```

在训练覆盖完整速度和附着范围的世界模型之前，还需要在 CarSim 中生成不同初速度
和路面附着系数对应的 `.sim` Run 文件，并填写
`config/carsim_case_manifest.local.csv`。不能仅修改 CSV 中的速度或 `mu` 数值来
替代真实 CarSim Run，否则数据标签与物理工况不一致。

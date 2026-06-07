# CarSim 与 Simulink 真联合仿真配置指南

## 1. 为什么不能直接创建一个空的 `vs_sf`

CarSim 的 VehicleSim S-Function 会根据具体 Run 数据集写入：

- Import 数量和顺序
- Export 数量和顺序
- CarSim 求解器步长
- Run 参数文件
- CarSim 安装路径与求解器信息

因此项目不能用普通 Simulink S-Function 占位块冒充 CarSim。正确流程是：

1. 在 CarSim 中配置一个真实 Run。
2. 使用 `Send to Simulink` 生成种子模型。
3. 项目脚本复制该 Run 对应的 VehicleSim S-Function。
4. 项目脚本自动接入压力、单位转换和数据日志。

## 2. CarSim Run 配置

### 2.1 车辆参数

复制一个直线制动 Run 和一个最接近的乘用车数据集。

按当前机制模型设置或校准：

| 参数 | 项目参考值 |
|---|---:|
| 总质量 | 1800 kg |
| 初速度 | 20–120 km/h |
| 制动压力 | 0–10 MPa |
| 路面附着系数 | 0.2 / 0.4 / 0.6 / 0.8 |
| 数据采样周期 | 0.05 s |

CarSim 内部求解步长建议保持 `0.001 s`，采集脚本会把输出重采样到 `0.05 s`。不要为了匹配机器学习数据而把整车求解步长直接调成 `0.05 s`。

CarSim 的质量通常分布在簧载和非簧载部分。应保证各部分总和约为 `1800 kg`，而不是只修改一个显示字段。

当前简化模型使用：

```text
kBrake = 3500 N/MPa
```

CarSim 的制动器使用更详细的制动转矩/压力关系。先按默认制动器完成联合仿真，再运行：

```matlab
calibrate_carsim_brake_gain("data/carsim_brake_sequence_dataset.csv")
```

评估 CarSim 低滑移区域的等效制动力增益是否接近 `3500 N/MPa`。

### 2.2 路面与试验过程

为以下组合建立或复制 CarSim Run：

```text
初速度：20、40、60、80、100、120 km/h
mu：0.2、0.4、0.6、0.8
```

基础道路采用平直道路。每个 Run 中设置正确的初速度和路面摩擦系数。

课程闭环可以先配置 24 个 Run。每个 Run 在 Simulink 侧使用多条随机压力曲线重复仿真，无需为每条压力曲线重新创建 CarSim Run。

## 3. Import 与 Export 配置

在 CarSim Run 的 `Models: Simulink` 配置中，按以下顺序加入 Import：

```text
1. IMP_PBK_L1
2. IMP_PBK_L2
3. IMP_PBK_R1
4. IMP_PBK_R2
```

四个通道分别对应四个车轮的制动压力。当前项目把同一个主缸压力复制给四轮。

按以下顺序加入 Export：

```text
1. Vx_SM
2. Ax_SM
```

项目默认假设：

```text
Vx_SM 单位：km/h
Ax_SM 单位：g
制动压力单位：MPa
```

如果 CarSim 数据集显示的 user unit 不同，修改：

```matlab
src/defaultCarSimConfig.m
```

中的：

```matlab
cfg.pressureToCarSim
cfg.speedToMps
cfg.accelToMps2
```

Import/Export 的数量和顺序必须与项目一致，因为 S-Function 只传输向量，不传输信号名称。

## 4. 生成种子模型

在 CarSim VS Browser 中：

1. 进入配置好的 Run。
2. 选择 `Models: Simulink`。
3. 确认 Import/Export 顺序。
4. 点击 `Send to Simulink`。
5. 将打开的模型保存为：

```text
models/carsim_seed_model.slx
```

种子模型必须包含真实的 CarSim/VehicleSim S-Function。

## 5. 自动生成项目联合仿真模型

在 MATLAB 中切换到项目根目录，运行：

```matlab
addpath("src");
addpath("scripts");
verify_carsim_prerequisites();
setup_carsim_cosim( ...
    "models/carsim_seed_model.slx", ...
    SimFilePath="F:\Carsim\UserData\simfile.sim", ...
    Overwrite=true);
```

`SimFilePath` 是本机 CarSim 生成的 `.sim` 描述文件路径。脚本会尝试从
种子模型目录、MATLAB 当前目录和 CarSim 安装目录下的 `UserData` 自动解析，
但在正式工程中建议显式传入绝对路径。

脚本会生成：

```text
models/carsim_brake_cosim.slx
results/carsim_interface_report.tsv
config/carsim_case_manifest.csv
```

`carsim_brake_cosim.slx` 包含：

- 随机压力时间序列输入
- `0–10 MPa` 饱和限制
- 四轮压力复制
- 真实 VehicleSim S-Function
- `Vx_SM` 与 `Ax_SM` 单位转换
- 速度、减速度、压力和 `mu` 日志

## 5.1 单工况联合仿真验收

生成联合模型后，先运行一个真实 CarSim 冒烟工况：

```matlab
report = verify_carsim_cosim_smoke( ...
    SimFilePath="F:\Carsim\UserData\simfile.sim", ...
    PressureMPa=2.0, ...
    StopTimeS=2.5, ...
    ExpectedInitialSpeedKph=80, ...
    ExpectedMu=0.85);
```

当前 `simfile.sim` 对应的 CarSim Run 为 `80 km/h`、路面 `mu=0.85`。如果重新
生成了其他 Run，应同时修改 `ExpectedInitialSpeedKph` 和 `ExpectedMu`。

验收脚本会检查：

- VehicleSim S-Function 是否能够编译并加载求解器
- 实际初速度与 CarSim Run 是否一致
- 制动压力是否真正进入联合模型
- 速度是否下降、纵向加速度是否为制动方向
- 输出是否包含 NaN 或无穷值
- 模型使用的 Simulink 求解器配置

输出文件：

```text
results/carsim_smoke_trajectory.csv
results/carsim_smoke_summary.json
```

冒烟测试通过后，验证正式数据采集器：

```matlab
summary = verify_carsim_dataset_smoke();
```

该脚本使用当前 `80 km/h、mu=0.85` 的 CarSim Run 生成一条随机压力轨迹，
并检查 `0.05 s` 重采样、训练字段、transition 标签、数据来源和有限数值。

输出：

```text
data/carsim_dataset_smoke.csv
results/carsim_dataset_smoke_summary.json
```

## 6. 配置不同 CarSim Run

打开：

```text
results/carsim_interface_report.tsv
```

在 `DialogParameter` 或 `MaskParameter` 中找到控制 CarSim `.sim`/Run 文件的参数名称。

当前 CarSim 2019.0 接口报告中的参数名称为：

```text
SIMFILE
```

项目默认使用该名称。其他 CarSim 版本如果显示不同名称，应在调用采集器时通过
`RunFileDialogParameter` 显式传入接口报告中的名称。

先复制模板：

```matlab
copyfile("config/carsim_case_manifest.csv", ...
    "config/carsim_case_manifest.local.csv");
```

然后在：

```text
config/carsim_case_manifest.local.csv
```

中填写每个工况对应的 `run_file`。

同一速度和 `mu` 的多个 replicate 可以共享同一个 Run 文件。

### 6.1 必须复制不同的 Run Control 数据集

仅反复修改同一个 CarSim Run，然后复制 `simfile.sim` 并重命名是不够的。
如果 `.sim` 内的：

```text
SET_MACRO $(ROOT_FILE_NAME)$ Run_xxx
```

始终相同，那么全部文件仍会读取同一个
`Results\Run_xxx\Run_all.par`。后一次运行会覆盖前一次工况。

正确做法是：

1. 在 CarSim Run Control 页面点击 `Duplicate`。
2. 为每个速度和 `mu` 组合建立独立 Run Control 数据集。
3. 每个 Run 引用对应的 Procedure 和 Road 数据集。
4. 分别运行或执行 `Send to Simulink`。
5. 复制每次生成的 `simfile.sim`，并按 `vXXX_muXXX.sim` 命名。
6. 确认每个 `.sim` 的 `ROOT_FILE_NAME` 均不同。

全部导出后运行：

```matlab
report = validate_carsim_run_library();
```

只有显示 `valid conditions: 24` 和 `result: PASS` 后，才能用于批量采集。

随后自动生成 120 条本机批量清单：

```matlab
cases = prepare_carsim_batch_manifest();
```

在运行完整批量采集前，先验证 6 个边界工况：

```matlab
summary = verify_carsim_run_matrix_smoke();
```

该测试覆盖：

```text
20 / 80 / 120 km/h
mu = 0.2 / 0.8
```

批量采集器会自动将 manifest 中的 `.sim` 文件复制到：

```text
%TEMP%\carsim_world_model_runs\
```

再传递给 VehicleSim。这样可规避 CarSim 2019 对包含空格或中文字符路径的兼容问题，
manifest 仍然保留项目目录中的原始规范路径。

## 7. 先做单工况验证

建议先只保留清单中的一行，然后运行：

```matlab
dataset = carsim_collect_dataset( ...
    "config/carsim_case_manifest.local.csv", ...
    "data/carsim_smoke_dataset.csv", ...
    ModelPath="models/carsim_brake_cosim.slx", ...
    RunFileDialogParameter="SIMFILE");
```

采集器会检查：

- CarSim 输出是否存在
- 输出是否为 timeseries
- 仿真数据是否包含 NaN
- 实际首帧速度是否与清单一致

如果清单写 `80 km/h`，但 CarSim 实际从 `40 km/h` 开始，脚本会直接报错，而不会把错误工况写入训练集。

## 8. 批量采集

单工况通过后，恢复完整清单并运行：

```matlab
summary = run_carsim_full_collection();
```

该入口会采集 120 条轨迹，并检查是否覆盖 24 个物理工况、每条轨迹是否包含有效
压力输入、初速度是否与 manifest 一致。停车附近 CarSim 可能产生很小的负速度，
采集器会按照本项目的一维速度定义将其截断为 0。

输出格式：

```text
trajectory_id
step
time_s
v_mps
a_mps2
pressure_MPa
mu
v_next_mps
a_next_mps2
initial_speed_kph
brake_utilization_reference
slip_risk_reference
source
```

前九列与当前 LSTM 数据接口兼容，因此训练命令只需要更换 CSV：

```powershell
python python/train_sequence_world_model.py --data data/carsim_brake_sequence_dataset.csv
```

## 9. 常见问题

### 找不到 CarSim S-Function

说明使用的不是 `Send to Simulink` 生成的模型，或 CarSim MATLAB 路径没有初始化。

### 输入端口或输出端口数量错误

回到 CarSim Run，重新确认 Import/Export 数量和顺序，再次 `Send to Simulink`。

### 速度单位错误

如果输出看起来缩小或放大了 `3.6` 倍，检查 `Vx_SM` user unit 和 `cfg.speedToMps`。

### 减速度放大约 `9.81` 倍

检查 `Ax_SM` 是 `g` 还是 `m/s^2`，相应修改 `cfg.accelToMps2`。

### 修改了 manifest 速度，但实际速度没有变化

manifest 中的速度只是元数据。真正的初速度必须由对应的 CarSim Run 设置。采集脚本会通过首帧速度检查发现这个问题。

### 是否可以动态修改 `mu`

当前稳定实现使用不同 CarSim Run/道路数据集表达不同 `mu`。动态路面摩擦输入需要额外配置 CarSim 可导入摩擦变量或 VS Commands，不同版本和轮胎模型的变量不同，不在代码中硬编码猜测。

## 10. 官方接口依据

CarSim 官方 ABS/Simulink 示例说明了以下要求：

- 通过 VS Browser 配置 Import/Export
- Import/Export 数量必须与 Simulink 模型匹配
- 使用 `Send to Simulink` 传递 Run 与求解器参数
- 四轮制动压力可通过 `IMP_PBK_*` 通道导入

参考：

```text
https://www.carsim.com/downloads/pdf/Simulink_ABS_Example.pdf
```

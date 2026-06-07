# World Model Brake System 30-Slide PPT Outline and Speaker Notes

This document is a storyboard for a roughly 30-slide final presentation. It is
designed to be converted into a full PPT deck after the team confirms the
storyline, chart choices, and speaking scope.

Recommended split:

| Speaker | Slides | Main responsibility |
|---|---:|---|
| A | 1-10 | Problem definition, project pipeline, mechanism baseline, data interface |
| B | 11-20 | CarSim co-simulation, CarSim dataset, LSTM/GRU ablation, CarSim-GRU |
| C | 21-30 | MPC planner, closed-loop stop, engineering deliverables, limitations, next steps |

Estimated total time: 24-28 minutes, depending on Q&A pace.

## Generated Figure and Table Assets

Run the asset generator from the project root:

```powershell
& "C:\Users\MrZang\anaconda3\condabin\conda.bat" run -n rl_env `
  python scripts/build_presentation_assets.py
```

Default output directory:

```text
results/presentation_assets/
```

Current preview output from this Codex session:

```text
C:\Users\MrZang\AppData\Local\Temp\world_model_presentation_assets
```

### New Chart Assets

| Asset | Recommended slide | Takeaway |
|---|---:|---|
| `01_dataset_inventory.png` | 4 | The project now has mechanism, sequence, and CarSim datasets. |
| `02_mechanism_dataset_coverage.png` | 7 | Baseline sampling covers speed, pressure, and adhesion broadly. |
| `03_mechanism_pressure_mu_response.png` | 8 | Higher adhesion supports stronger deceleration before saturation. |
| `04_mechanism_sequence_examples.png` | 11 | Recurrent models see pressure and vehicle-state histories. |
| `05_model_metrics_rmse_summary.png` | 15 / 24 | CarSim acceleration is the hardest prediction target. |
| `06_recurrent_ablation_rmse_params.png` | 17 | GRU S5 H64 L1 is compact and strong on acceleration RMSE. |
| `07_recurrent_tradeoff_scatter.png` | 18 | Larger recurrent networks are not automatically better. |
| `08_carsim_coverage_heatmap.png` | 14 | Every speed/adhesion condition is represented in the full CarSim dataset. |
| `09_carsim_peak_decel_by_mu.png` | 15 | CarSim produces expected adhesion-limited deceleration layers. |
| `10_carsim_matrix_smoke.png` | 13 | Boundary smoke tests validate low/high adhesion response. |
| `11_carsim_smoke_trajectory.png` | 12 | Co-simulation responds to pressure input and returns finite signals. |
| `12_carsim_pressure_profile_examples.png` | 14 | CarSim data uses varied pressure commands, not one fixed pressure. |
| `13_carsim_gru_metrics.png` | 20 | Speed prediction remains strong; acceleration is the honest hard target. |
| `14_mpc_stop_result.png` | 25 | The sampled planner stops safely within 0.156 m of target distance. |

### Existing Figure Assets

| Asset | Recommended slide | Use |
|---|---:|---|
| `results/mu_response.png` | 8 | Road adhesion mechanism response. |
| `results/prediction_compare.png` | 9 | MLP baseline prediction comparison. |
| `results/training_loss.png` | 9 | MATLAB MLP training convergence. |
| `results/sequence_training_loss.png` | 19 | Mechanism sequence GRU/LSTM training convergence. |
| `results/carsim_gru_training_loss.png` | 19 | CarSim-GRU training convergence. |
| `results/safety_planning_scenario.png` | 23 | Early one-step safety barrier demonstration. |
| `results/mpc_stop_scenario.png` | 25 | Existing MPC stopping result plot. |

### Table Assets

| Asset | Recommended slide | Use |
|---|---:|---|
| `tables/dataset_inventory.md` | 4 | Dataset row-count scorecard. |
| `tables/model_metrics_summary.md` | 24 | Model metrics comparison. |
| `tables/recurrent_ablation.md` | 17 | Full ablation table. |
| `tables/carsim_matrix_smoke.md` | 13 | Boundary smoke-test table. |
| `tables/carsim_gru_metrics.md` | 20 | CarSim-GRU RMSE/MAE/R2 table. |
| `asset_manifest.csv` | Appendix | Figure registry. |

## 30-Slide Storyboard

### Slide 1. Title

Visual: clean title slide with project name and three-speaker split.

On-slide bullets:

- World Model in Brake System
- Simulink / CarSim co-simulation
- GRU-PINN sequence model
- Sampled MPC stopping planner

Speaker note:

各位老师、同学好，我们汇报的题目是基于世界模型的一维纵向制动决策规划。这个项目从一个简化的纵向制动机理模型出发，逐步扩展到 CarSim 高保真联合仿真、GRU 时序世界模型和采样式 MPC 规划器。今天我们会重点展示三件事：第一，数据和仿真环境如何建立；第二，为什么从 MLP 升级到 GRU 并做消融实验；第三，世界模型如何进入上层规划闭环，完成一维安全刹停。

### Slide 2. One-Sentence Objective

Visual: objective card plus input/output diagram.

On-slide bullets:

- Input: speed, acceleration, pressure, road adhesion, obstacle distance
- Output: next state prediction and braking action
- Goal: stop safely, accurately, and smoothly before an obstacle

Speaker note:

我们的问题可以浓缩成一句话：给定车辆当前状态和前方障碍物距离，系统需要在线选择制动主缸压力，让车辆既不碰撞，又尽量停在目标安全距离附近，同时避免过大的减速度。这里世界模型不是单独做预测，而是为规划器提供一个快速、可调用的虚拟动力学环境。

### Slide 3. Why This Is More Than System Identification

Visual: contrast table, "identification" vs "planning by prediction".

On-slide bullets:

- System identification: learn dynamics only
- Planning by prediction: use learned dynamics to choose actions
- The planner repeatedly simulates futures before executing one action

Speaker note:

如果只是训练 MLP 或 GRU 去拟合下一时刻速度，这只能算系统辨识。我们的目标是进一步把预测模型放进规划环节，让控制器在执行前先“脑内推演”多条未来压力曲线，比较风险和代价，再选择当前最合适的压力。这就是从系统辨识走向预测式决策的关键区别。

### Slide 4. Project Data Inventory

Visual: `01_dataset_inventory.png` plus small scorecard.

On-slide bullets:

- 30,000 mechanism one-step rows
- 16,000 mechanism sequence rows
- 13,070 raw CarSim transitions
- 10,924 CarSim training transitions

Speaker note:

这张图先说明工程当前的数据规模。我们保留了三万条单步机理数据，用于快速验证 MLP；一万六千行机理时序数据，用于 LSTM 和 GRU；同时已经通过 CarSim/Simulink 联合仿真得到一万三千零七十条高保真状态转移，并进一步清洗出一万零九百二十四条训练数据。也就是说，现在的数据链路已经不只停留在简化模型。

### Slide 5. End-to-End Workflow

Visual: workflow diagram.

On-slide bullets:

- Mechanism model for reproducible baseline
- CarSim for high-fidelity pseudo-real data
- GRU/PINN as chassis world model
- Sampled MPC as upper-level planner

Speaker note:

整体流程分成四层。第一层是环境，包括简化机理模型和 CarSim。第二层是数据集，把不同来源统一成相同的输入输出格式。第三层是世界模型，包含 MLP 基线、LSTM/GRU 消融和 PINN 约束。第四层是规划器，它调用世界模型预测未来，再把第一步压力交给物理环境执行。这个结构保证后续替换数据源或模型结构时，不需要重写全部代码。

### Slide 6. Mechanism Baseline Equations

Visual: formula panel and parameter table.

On-slide bullets:

- `F_brake = k * P`
- `F_actual = min(F_brake, mu * m * g)`
- `a_next = -F_actual / m`
- `v_next = max(v + a_next * dt, 0)`

Speaker note:

机理模型使用一个可解释的纵向制动近似。制动力与主缸压力线性相关，但实际制动力不能超过路面附着上限。之后通过牛顿第二定律计算减速度，再用离散积分更新速度。车辆质量取一千八百千克，采样周期零点零五秒。这个模型虽然简化，但非常适合做基线、单元测试和规划器初始验证。

### Slide 7. Mechanism Dataset Coverage

Visual: `02_mechanism_dataset_coverage.png`.

On-slide bullets:

- Speed coverage: 20-120 km/h equivalent range
- Pressure coverage: 0-10 MPa
- Adhesion coverage: 0.2 / 0.4 / 0.6 / 0.8

Speaker note:

这张图展示机理单步数据的采样覆盖。速度、压力和附着系数都覆盖了制动场景中的主要范围，这保证 MLP 不只是记住少数工况。对于期末汇报来说，这张图能够回答“你们的数据是不是太单一”的问题。我们可以强调，机理数据用于快速闭环，不代表最终真实世界，但它为模型和规划器接口打下了基础。

### Slide 8. Adhesion-Limited Braking Response

Visual: `03_mechanism_pressure_mu_response.png` or `results/mu_response.png`.

On-slide bullets:

- Higher pressure increases deceleration only before saturation
- Low road adhesion caps braking earlier
- This gives the model an interpretable physical prior

Speaker note:

这张图体现路面附着限制。压力增加时，减速度不会无限增大，因为实际制动力受到 μmg 的上限约束。低附着路面更早进入饱和，高附着路面可以支持更强制动。这个规律不仅能解释数据，也能帮助我们在后面的 PINN 和规划代价中加入物理口径。

### Slide 9. MLP Baseline Result

Visual: `results/prediction_compare.png` plus `results/world_model_metrics.csv` table.

On-slide bullets:

- One-step dynamics can be accurately learned
- MLP validates data generation, normalization, and inference
- Limitation: no explicit history dependence

Speaker note:

第一版世界模型是 MLP，用来验证单步动力学是否可学习。从预测对比图可以看到，模型输出与机理标签高度重合。这个结果说明数据生成、归一化、训练和推理链路是正确的。但 MLP 的限制也很清楚：它只看当前状态，无法表达压力建立、液压滞后和轮胎状态随时间变化的影响，所以它适合作为基线，不适合作为最终时序底座。

### Slide 10. Unified Dataset Schema

Visual: table of dataset columns.

On-slide bullets:

- `trajectory_id`, `step`, `time_s`
- `v_mps`, `a_mps2`, `pressure_MPa`, `mu`
- `v_next_mps`, `a_next_mps2`
- Extra CarSim fields are retained but not required

Speaker note:

为了让机理模型和 CarSim 数据都能进入同一套训练代码，我们设计了统一数据接口。核心字段包括当前速度、当前加速度、压力、附着系数，以及下一时刻速度和加速度。CarSim 可以额外保留初速度、来源、参考风险等字段，但训练接口只依赖前九个核心字段。这个设计减少了后续工程切换成本。

### Slide 11. Sequence Modeling Data

Visual: `04_mechanism_sequence_examples.png`.

On-slide bullets:

- Input becomes the latest K steps
- Default K = 5
- Features: speed, acceleration, pressure, adhesion
- Target: next speed and acceleration

Speaker note:

从这一页开始进入同学 B 的模型部分。为了建模制动过程的历史依赖，我们把输入从单个点改成最近五个时间步的序列。每一步包含速度、加速度、压力和附着系数。这样模型能看到压力如何逐步建立、速度如何连续下降，而不是只在当前点做静态映射。

### Slide 12. CarSim Co-Simulation Interface

Visual: block diagram of Simulink pressure input to VehicleSim S-Function.

On-slide bullets:

- Import: `IMP_PBK_L1/L2/R1/R2`
- Export: `Vx_SM`, `Ax_SM`
- Same pressure command sent to four wheels
- `SIMFILE` selects the CarSim Run

Speaker note:

CarSim 联合仿真的关键是 VehicleSim S-Function 接口。我们从 Simulink 输入四个制动压力信号，对应四个车轮；CarSim 输出纵向速度和纵向加速度。当前 CarSim 2019 的运行文件参数名是 `SIMFILE`，因此脚本会把不同工况的 `.sim` 文件切换到同一个联合仿真模型里运行。

### Slide 13. CarSim Smoke Verification

Visual: `11_carsim_smoke_trajectory.png`.

On-slide bullets:

- 80 km/h, mu = 0.85, pressure = 2 MPa
- 2.5 s simulation, 2501 samples
- Final speed: 58.373 km/h
- Minimum acceleration: -3.238 m/s^2
- Result: PASS

Speaker note:

这一页展示单工况冒烟测试。输入是八十公里每小时、附着系数零点八五、二兆帕制动压力，仿真两点五秒。结果显示速度确实下降，压力信号有效，输出没有 NaN，最小加速度约负三点二三八米每二次方秒。这一步验证的是联合仿真通道本身：压力能进去，车辆响应能出来。

### Slide 14. CarSim Run Matrix Smoke Test

Visual: `10_carsim_matrix_smoke.png` plus table `carsim_matrix_smoke.md`.

On-slide bullets:

- 6 representative boundary cases
- Speeds: 20 / 80 / 120 km/h
- Road adhesion: 0.2 and 0.8
- All 6 cases valid

Speaker note:

单工况通过之后，我们进一步检查边界工况矩阵。这里选择低、中、高三个初速度，并在低附着零点二和高附着零点八下各跑一次，总计六个代表性工况。六个工况都通过了初速度匹配、制动响应和有效输出检查。图中可以看到，高附着工况的峰值减速度明显更强，这符合物理预期。

### Slide 15. Full CarSim Dataset Coverage

Visual: `08_carsim_coverage_heatmap.png` and `12_carsim_pressure_profile_examples.png`.

On-slide bullets:

- 6 speeds x 4 adhesion levels
- 5 pressure trajectories per condition
- 120 total trajectories
- 13,070 raw transitions

Speaker note:

完整 CarSim 数据集覆盖六档初速度和四档附着系数，每个物理工况下使用五条不同压力轨迹，总计一百二十条轨迹。左侧热力图显示每个速度和附着组合都有数据，右侧压力轨迹说明我们不是只用恒定压力，而是包含变化压力曲线。这样训练出来的模型更接近实际控制中会遇到的输入序列。

### Slide 16. CarSim Physical Response

Visual: `09_carsim_peak_decel_by_mu.png`.

On-slide bullets:

- mu = 0.2: peak deceleration near 2 m/s^2
- mu = 0.8: peak deceleration above 7 m/s^2
- CarSim response follows adhesion-limited layers

Speaker note:

这张图从完整数据集中汇总每个工况的峰值减速度。可以看到不同附着系数形成了非常清晰的分层：零点二低附着接近二米每二次方秒，零点八高附着超过七米每二次方秒。这个结果说明 CarSim 数据不仅能跑通，而且在物理趋势上符合路面附着限制。

### Slide 17. Why GRU Instead of Only LSTM

Visual: compact architecture diagram.

On-slide bullets:

- LSTM: expressive but more parameters
- GRU: fewer gates, lower inference cost
- Planner calls the model many times per control step
- Need accuracy and computational efficiency

Speaker note:

在规划器里，世界模型不是只调用一次，而是每个控制时刻都要对很多候选压力序列反复滚动预测。因此模型不仅要准，还要轻量。LSTM 表达能力强，但参数更多；GRU 门结构更简洁，通常能用更少参数捕捉短期动态。我们没有凭直觉选择，而是做了统一消融实验。

### Slide 18. LSTM/GRU Ablation Design

Visual: experiment design table.

On-slide bullets:

- Recurrent type: LSTM vs GRU
- Sequence length: 5 vs 50
- Hidden size/layers: 64x1 vs 128x2
- Same seed, split, epochs, PINN weight

Speaker note:

消融实验采用科学对比方式。我们固定随机种子、轨迹级划分、四十个训练轮次和物理损失权重，只改变循环单元、序列长度和模型深度。这样得到的差异主要来自结构本身，而不是训练设置变化。这个实验也回应了一个常见问题：是不是模型越深、序列越长就越好。

### Slide 19. Ablation Result

Visual: `06_recurrent_ablation_rmse_params.png`.

On-slide bullets:

- Recommended: GRU S5 H64 L1
- Parameters: 17,730
- v RMSE: 0.0648 m/s
- a RMSE: 0.0431 m/s^2

Speaker note:

结果显示，推荐配置是短序列、单层、六十四隐藏单元的 GRU。它只有一万七千七百三十个参数，但速度 RMSE 达到零点零六四八米每秒，减速度 RMSE 达到零点零四三一米每二次方秒。与同配置 LSTM 相比，它参数更少，减速度误差显著更低，非常适合作为后续 MPC 的预测底座。

### Slide 20. Model Size vs Error Trade-Off

Visual: `07_recurrent_tradeoff_scatter.png`.

On-slide bullets:

- Larger model does not guarantee lower error
- Long sequence helps some speed metrics but hurts acceleration
- GRU short sequence is the best engineering compromise

Speaker note:

这张散点图进一步说明，模型变大并不自动带来更好的规划价值。长序列深模型在某些速度指标上可能略好，但参数量上升接近一个数量级，而且减速度误差未必同步改善。因为规划器特别依赖减速度预测和实时调用成本，所以我们选择 GRU S5 H64 L1，而不是盲目堆深网络。

### Slide 21. CarSim-GRU Training Setup

Visual: training configuration scorecard plus `results/carsim_gru_training_loss.png`.

On-slide bullets:

- Data source: CarSim
- GRU S=5, H=64, L=1
- 96 training trajectories, 24 validation trajectories
- 40 epochs, CUDA, 17.2 s

Speaker note:

在选定结构后，我们把同一套 GRU-PINN 训练到 CarSim 数据上。训练采用轨迹级划分，而不是随机打散相邻时间点，避免数据泄漏。训练集九十六条轨迹，验证集二十四条轨迹，训练四十轮，GPU 用时约十七点二秒。这说明模型训练成本很低，便于反复调参。

### Slide 22. CarSim-GRU Metrics

Visual: `13_carsim_gru_metrics.png` plus `carsim_gru_metrics.md`.

On-slide bullets:

- v_next RMSE: 0.1173 m/s, R2 = 0.99981
- a_next RMSE: 0.4493 m/s^2, R2 = 0.92929
- CarSim acceleration is more nonlinear than mechanism data

Speaker note:

CarSim-GRU 在验证集上速度预测仍然非常准确，RMSE 为零点一一七三米每秒，R 方接近一。减速度预测的 RMSE 为零点四四九三米每二次方秒，R 方为零点九二九二九。这个误差比机理数据高是合理的，因为 CarSim 包含更复杂的轮胎非线性、车身俯仰和停车附近动态。我们把它作为真实难度的体现，而不是掩盖掉。

### Slide 23. Mechanism vs CarSim Difficulty

Visual: `05_model_metrics_rmse_summary.png`.

On-slide bullets:

- Mechanism labels are smoother and easier
- CarSim speed remains easy to predict
- CarSim acceleration exposes high-fidelity dynamics

Speaker note:

这张图把不同数据源和模型的 RMSE 放在一起比较。简化机理数据更平滑，因此模型误差非常低；CarSim 速度仍然容易预测，但加速度误差明显更高。这个对比有助于解释为什么要引入 CarSim：它让模型面对更真实的物理复杂性，也让评价指标更加诚实。

### Slide 24. Planning Problem Formulation

Visual: state/action/cost table.

On-slide bullets:

- State: speed, distance, adhesion
- Action: master-cylinder pressure
- Horizon: candidate pressure sequence
- Cost: distance, comfort, smoothness, collision, not-stop penalty

Speaker note:

接下来进入同学 C 的规划部分。规划器的状态包括当前速度、障碍物距离和附着系数，动作是主缸压力。每次规划不是只选一个压力点，而是采样一段未来压力序列。代价函数综合终点距离误差、减速度舒适性、压力平滑、碰撞惩罚和未刹停惩罚。

### Slide 25. Sampled MPC Algorithm

Visual: four-step loop diagram.

On-slide bullets:

1. Sample pressure sequences
2. Roll out future trajectory with world model
3. Score each sequence by cost
4. Execute only the first pressure

Speaker note:

我们采用的是采样式 MPC，而不是复杂的解析梯度优化。每个控制时刻生成多条平滑压力曲线，世界模型对每条曲线进行未来展开，然后用代价函数排序。选出最优序列后，只执行第一步压力，下一时刻根据反馈重新规划。这个方法直观、可解释，也方便后续升级到 MPPI 或 CEM。

### Slide 26. One-Step Safety Barrier Baseline

Visual: `results/safety_planning_scenario.png`.

On-slide bullets:

- Earlier safety layer before full MPC
- Select pressure from safety constraint
- Helps debug distance and stopping logic

Speaker note:

在完整 MPC 之前，我们先实现了一个更简单的一步安全屏障，用于验证距离更新、速度更新和压力选择逻辑。它不是最终控制器，但对于工程调试非常重要。先把简单闭环跑通，再升级到多步采样规划，可以降低开发风险。

### Slide 27. Closed-Loop MPC Stopping Result

Visual: `14_mpc_stop_result.png`.

On-slide bullets:

- v0 = 80 km/h
- x0 = 65 m
- mu = 0.6
- d_safe = 2 m
- final distance = 1.844 m
- error = 0.156 m

Speaker note:

这张图展示当前完整闭环刹停结果。初始速度八十公里每小时，障碍物距离六十五米，附着系数零点六，目标安全距离两米。规划器前段使用较温和的压力，后段提高压力，最终车辆在约五点零五秒停止，剩余距离一点八四四米，与目标相差零点一五六米，没有碰撞。

### Slide 28. Honest Boundary of the Current Closed Loop

Visual: "completed vs next integration" table.

On-slide bullets:

- Completed: CarSim dataset and CarSim-GRU training
- Completed: MPC with mechanism execution environment
- Not yet claimed: live CarSim-in-the-loop MPC execution
- Next: send each MPC action to CarSim and replan from CarSim feedback

Speaker note:

这里需要明确项目口径。我们已经完成了 CarSim 数据采集、工况验证和 CarSim-GRU 训练；也完成了机制环境下的 MPC 闭环刹停。但目前还不能说已经完成 CarSim 在线闭环 MPC，因为刹停演示的执行环境仍是简化机理模型。下一步要做的是把每个实际压力动作发送给 CarSim，再用 CarSim 反馈滚动重规划。

### Slide 29. Engineering Deliverables

Visual: repository map table.

On-slide bullets:

- MATLAB scripts and Simulink models
- CarSim setup and validation tools
- Python GRU/LSTM training pipeline
- MPC planner
- README, documentation, and presentation assets

Speaker note:

从工程交付角度看，仓库已经包含多个可复现模块。MATLAB 侧有机理模型、CarSim 联调脚本和数据采集脚本；Python 侧有时序数据生成、GRU/LSTM 训练、消融实验和 MPC 规划器；文档侧有中英文 README、CarSim 配置指南、消融实验说明和 PPT 资产生成脚本。这个项目可以继续扩展，而不是一次性脚本。

### Slide 30. Conclusion and Next Steps

Visual: three-column summary: data, model, planner.

On-slide bullets:

- Data: mechanism + CarSim high-fidelity trajectories
- Model: compact GRU/PINN selected by ablation
- Planner: sampled MPC achieves safe stopping
- Next: live CarSim MPC, friction changes, MPPI/CEM, robustness

Speaker note:

最后总结。我们已经把项目从简单的机理数据拟合，推进到 CarSim 高保真数据、GRU-PINN 世界模型和采样式 MPC 决策规划。最重要的结论是，世界模型的价值不只是预测精度，而是能否进入规划闭环。下一阶段重点是实现 CarSim 在线执行闭环，引入附着系数突变、噪声和制动热衰退场景，并把随机搜索升级为 MPPI 或 CEM，提高实时性和鲁棒性。谢谢大家。


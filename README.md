# World Model in Brake System

This project implements a longitudinal braking world-model loop, from mechanism-generated pseudo data to learned prediction and one-dimensional safety planning.

## Current MATLAB Loop

1. Mechanism model: simplified longitudinal braking dynamics.
2. Data generation: random speed, brake pressure, and road adhesion coefficient.
3. World model: compact MLP that learns `S_t + A_t -> S_{t+1}`.
4. Safety planning: a shield evaluates candidate brake pressures and limits unsafe actions.

Open MATLAB in this folder and run:

```matlab
scripts/run_all
```

The script writes datasets, trained model files, plots, and a generated Simulink model into `data/`, `results/`, and `models/`. It now also creates `data/brake_sequence_dataset.csv` for sequence-model training.

## Advanced World-Model Planning Loop

The next-stage implementation is documented in `docs/engineering_implementation_plan.md`.

Generate sequence data with Python if MATLAB is not available:

```powershell
python python/generate_sequence_dataset.py --out data/brake_sequence_dataset.csv
```

When the CarSim S-Function model is ready, use `scripts/carsim_collect_dataset_template.m` as the batch-collection starting point and export the same trajectory CSV schema.

Train an LSTM world model with a lightweight PINN velocity-consistency loss:

```powershell
python python/train_sequence_world_model.py --data data/brake_sequence_dataset.csv --epochs 40 --sequence-len 5 --pinn-weight 0.05
```

Run the one-dimensional sampled MPC stopping demo:

```powershell
python python/plan_stop_mpc.py --model models/world_model_lstm.pt
```

The Python loop writes:

- `models/world_model_lstm.pt`
- `results/sequence_world_model_metrics.csv`
- `results/sequence_training_loss.png`
- `results/mpc_stop_scenario.csv`
- `results/mpc_stop_scenario.png`

| chart | takeaway |
| --- | --- |
| 01_dataset_inventory.png | The project now contains mechanism, sequence, and CarSim datasets. |
| 02_mechanism_dataset_coverage.png | The baseline data covers speed, pressure, and adhesion broadly. |
| 03_mechanism_pressure_mu_response.png | Higher adhesion supports stronger deceleration before saturation. |
| 04_mechanism_sequence_examples.png | The recurrent model sees full pressure and vehicle-state histories. |
| 05_model_metrics_rmse_summary.png | CarSim-GRU keeps high speed accuracy but acceleration is more challenging. |
| 06_recurrent_ablation_rmse_params.png | GRU S5 H64 L1 is compact and wins the key acceleration metric. |
| 07_recurrent_tradeoff_scatter.png | Bigger recurrent networks are not automatically better for this task. |
| 08_carsim_coverage_heatmap.png | Every speed/adhesion condition is represented in the full CarSim dataset. |
| 09_carsim_peak_decel_by_mu.png | CarSim produces the expected adhesion-limited deceleration layers. |
| 10_carsim_matrix_smoke.png | Low-mu and high-mu boundary cases produce distinct, valid braking responses. |
| 11_carsim_smoke_trajectory.png | The co-simulation responds to pressure input and returns finite vehicle signals. |
| 12_carsim_pressure_profile_examples.png | The CarSim data includes varied braking commands rather than one fixed pressure. |
| 13_carsim_gru_metrics.png | Speed prediction remains very strong; acceleration is the honest hard target. |
| 14_mpc_stop_result.png | The sampled planner stops safely within 0.156 m of the target distance. |

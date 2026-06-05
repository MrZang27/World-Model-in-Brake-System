%RUN_ALL Execute Scheme A MATLAB/Simulink engineering loop.

clear;
clc;

projectRoot = fileparts(fileparts(mfilename('fullpath')));
cd(projectRoot);
addpath(fullfile(projectRoot, 'src'));
addpath(fullfile(projectRoot, 'scripts'));

dataDir = fullfile(projectRoot, 'data');
resultsDir = fullfile(projectRoot, 'results');
modelsDir = fullfile(projectRoot, 'models');
if ~exist(dataDir, 'dir'), mkdir(dataDir); end
if ~exist(resultsDir, 'dir'), mkdir(resultsDir); end
if ~exist(modelsDir, 'dir'), mkdir(modelsDir); end

fprintf('1/5 Generating mechanism data...\n');
data = generateBrakeDataset(30000, fullfile(dataDir, 'brake_dataset.csv'));
generateBrakeSequenceDataset(800, 120, fullfile(dataDir, 'brake_sequence_dataset.csv'));

fprintf('2/5 Training world model...\n');
[model, history] = trainWorldModel(data.X, data.Y, ...
    HiddenSize=32, Epochs=220, BatchSize=256, LearnRate=0.004);
save(fullfile(modelsDir, 'world_model_mlp.mat'), 'model', 'history');

fprintf('3/5 Evaluating world model...\n');
metrics = evaluateWorldModel(model, data.X, data.Y);
metricsTable = table(["v_next"; "a_next"], metrics.mse(:), metrics.mae(:), metrics.r2(:), ...
    'VariableNames', {'output', 'mse', 'mae', 'r2'});
writetable(metricsTable, fullfile(resultsDir, 'world_model_metrics.csv'));
disp(metricsTable);

fprintf('4/5 Running safety-planning scenario...\n');
scenario = simulateSafetyScenario(model);
writetable(scenario, fullfile(resultsDir, 'safety_planning_scenario.csv'));
plotClosedLoopResults(data, history, metrics, scenario, resultsDir);

fprintf('5/5 Generating Simulink mechanism model...\n');
create_simulink_brake_model();

fprintf('\nDone. Key outputs:\n');
fprintf('  Dataset: %s\n', fullfile(dataDir, 'brake_dataset.csv'));
fprintf('  Sequence dataset: %s\n', fullfile(dataDir, 'brake_sequence_dataset.csv'));
fprintf('  Model:   %s\n', fullfile(modelsDir, 'world_model_mlp.mat'));
fprintf('  Metrics: %s\n', fullfile(resultsDir, 'world_model_metrics.csv'));
fprintf('  Figures: %s\n', resultsDir);

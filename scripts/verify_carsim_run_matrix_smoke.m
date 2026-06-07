function summary = verify_carsim_run_matrix_smoke(options)
%VERIFY_CARSIM_RUN_MATRIX_SMOKE Test switching among boundary CarSim Runs.

arguments
    options.ModelPath (1,1) string = fullfile("models", "carsim_brake_cosim.slx")
    options.RunDirectory (1,1) string = fullfile("config", "carsim_runs")
    options.StopTimeS (1,1) double {mustBePositive} = 3.0
    options.OutputCsv (1,1) string = fullfile("data", "carsim_matrix_smoke.csv")
    options.SummaryCsv (1,1) string = fullfile("results", "carsim_matrix_smoke_summary.csv")
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "src"));
addpath(fullfile(projectRoot, "scripts"));

validate_carsim_run_library( ...
    RunDirectory=options.RunDirectory, ...
    FailOnInvalid=true);

conditions = [ ...
    20, 0.2; ...
    20, 0.8; ...
    80, 0.2; ...
    80, 0.8; ...
    120, 0.2; ...
    120, 0.8];
n = size(conditions, 1);
case_id = (1:n)';
initial_speed_kph = conditions(:, 1);
mu = conditions(:, 2);
replicate = ones(n, 1);
pressure_seed = 20260607 + case_id;
stop_time_s = repmat(options.StopTimeS, n, 1);
run_file = strings(n, 1);
runDirectory = absoluteProjectPath(projectRoot, options.RunDirectory);
for i = 1:n
    run_file(i) = fullfile(runDirectory, sprintf( ...
        "v%03d_mu%03d.sim", initial_speed_kph(i), round(100 * mu(i))));
end
manifest = table(case_id, initial_speed_kph, mu, replicate, ...
    pressure_seed, stop_time_s, run_file);

dataset = carsim_collect_dataset( ...
    manifest, options.OutputCsv, ...
    ModelPath=options.ModelPath, ...
    RunFileDialogParameter="SIMFILE", ...
    FailOnSpeedMismatch=true, ...
    SaveRawOutputs=false);

groups = findgroups(dataset.trajectory_id);
observed_initial_speed_kph = splitapply( ...
    @(value) value(1) * 3.6, dataset.v_mps, groups);
observed_final_speed_kph = splitapply( ...
    @(value) value(end) * 3.6, dataset.v_next_mps, groups);
minimum_acceleration_mps2 = splitapply( ...
    @min, dataset.a_next_mps2, groups);
maximum_pressure_mpa = splitapply( ...
    @max, dataset.pressure_MPa, groups);
row_count = splitapply(@numel, dataset.step, groups);

summary = table(case_id, initial_speed_kph, mu, ...
    observed_initial_speed_kph, observed_final_speed_kph, ...
    minimum_acceleration_mps2, maximum_pressure_mpa, row_count);
summary.speed_error_kph = abs( ...
    summary.observed_initial_speed_kph - summary.initial_speed_kph);
summary.speed_match = summary.speed_error_kph <= 5;
summary.braking_response = ...
    summary.observed_final_speed_kph < summary.observed_initial_speed_kph & ...
    summary.minimum_acceleration_mps2 < -0.05 & ...
    summary.maximum_pressure_mpa > 0.1;
summary.valid = summary.speed_match & summary.braking_response;

summaryPath = absoluteProjectPath(projectRoot, options.SummaryCsv);
summaryFolder = fileparts(summaryPath);
if strlength(summaryFolder) > 0 && ~isfolder(summaryFolder)
    mkdir(summaryFolder);
end
writetable(summary, summaryPath);

disp(summary);
fprintf("CarSim Run-matrix smoke result: %s (%d/%d valid)\n", ...
    passFail(all(summary.valid)), nnz(summary.valid), height(summary));
if ~all(summary.valid)
    error("CarSim:RunMatrixSmokeFailed", ...
        "One or more boundary CarSim Run conditions failed.");
end
end

function pathValue = absoluteProjectPath(projectRoot, pathValue)
pathValue = string(pathValue);
if ~isAbsolutePath(pathValue)
    pathValue = fullfile(projectRoot, pathValue);
end
end

function tf = isAbsolutePath(pathValue)
pathValue = char(pathValue);
tf = ~isempty(regexp(pathValue, "^[A-Za-z]:[\\/]", "once")) || ...
    startsWith(pathValue, "\\") || startsWith(pathValue, "/");
end

function text = passFail(value)
if value
    text = "PASS";
else
    text = "FAIL";
end
end

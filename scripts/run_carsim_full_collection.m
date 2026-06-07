function summary = run_carsim_full_collection(options)
%RUN_CARSIM_FULL_COLLECTION Collect and validate the full CarSim dataset.

arguments
    options.ManifestPath (1,1) string = ...
        fullfile("config", "carsim_case_manifest.local.csv")
    options.OutputCsv (1,1) string = ...
        fullfile("data", "carsim_brake_sequence_dataset.csv")
    options.ModelPath (1,1) string = ...
        fullfile("models", "carsim_brake_cosim.slx")
    options.SummaryCsv (1,1) string = ...
        fullfile("results", "carsim_full_dataset_summary.csv")
    options.SaveRawOutputs (1,1) logical = false
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "src"));
addpath(fullfile(projectRoot, "scripts"));

validate_carsim_run_library(FailOnInvalid=true);
if ~isfile(options.ManifestPath)
    prepare_carsim_batch_manifest(OutputCsv=options.ManifestPath);
end

dataset = carsim_collect_dataset( ...
    options.ManifestPath, options.OutputCsv, ...
    ModelPath=options.ModelPath, ...
    RunFileDialogParameter="SIMFILE", ...
    FailOnSpeedMismatch=true, ...
    SaveRawOutputs=options.SaveRawOutputs);

groups = findgroups(dataset.trajectory_id);
case_id = splitapply(@(value) value(1), dataset.trajectory_id, groups);
initial_speed_kph = splitapply( ...
    @(value) value(1), dataset.initial_speed_kph, groups);
mu = splitapply(@(value) value(1), dataset.mu, groups);
row_count = splitapply(@numel, dataset.step, groups);
observed_initial_speed_kph = splitapply( ...
    @(value) value(1) * 3.6, dataset.v_mps, groups);
observed_final_speed_kph = splitapply( ...
    @(value) value(end) * 3.6, dataset.v_next_mps, groups);
maximum_pressure_mpa = splitapply(@max, dataset.pressure_MPa, groups);
minimum_acceleration_mps2 = splitapply(@min, dataset.a_next_mps2, groups);

summary = table(case_id, initial_speed_kph, mu, row_count, ...
    observed_initial_speed_kph, observed_final_speed_kph, ...
    maximum_pressure_mpa, minimum_acceleration_mps2);
summary.speed_error_kph = abs( ...
    summary.observed_initial_speed_kph - summary.initial_speed_kph);
summary.valid = summary.row_count >= 5 & ...
    summary.speed_error_kph <= 5 & ...
    summary.maximum_pressure_mpa > 0.1 & ...
    isfinite(summary.minimum_acceleration_mps2);

summaryPath = absoluteProjectPath(projectRoot, options.SummaryCsv);
summaryFolder = fileparts(summaryPath);
if strlength(summaryFolder) > 0 && ~isfolder(summaryFolder)
    mkdir(summaryFolder);
end
writetable(summary, summaryPath);

conditionCount = height(unique( ...
    summary(:, ["initial_speed_kph", "mu"])));
fprintf("\nFull CarSim dataset verification\n");
fprintf("  transitions:       %d\n", height(dataset));
fprintf("  trajectories:      %d\n", height(summary));
fprintf("  physical conditions: %d\n", conditionCount);
fprintf("  valid trajectories: %d/%d\n", ...
    nnz(summary.valid), height(summary));
fprintf("  result:            %s\n", passFail(all(summary.valid)));
fprintf("  dataset:           %s\n", ...
    absoluteProjectPath(projectRoot, options.OutputCsv));
fprintf("  summary:           %s\n", summaryPath);

if height(summary) ~= 120 || conditionCount ~= 24 || ~all(summary.valid)
    error("CarSim:FullDatasetValidationFailed", ...
        "The full CarSim dataset is incomplete or contains invalid trajectories.");
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

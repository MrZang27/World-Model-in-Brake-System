function summary = verify_carsim_dataset_smoke(options)
%VERIFY_CARSIM_DATASET_SMOKE Validate the production CarSim data collector.

arguments
    options.ModelPath (1,1) string = fullfile("models", "carsim_brake_cosim.slx")
    options.SimFilePath (1,1) string = "F:\Carsim\UserData\simfile.sim"
    options.InitialSpeedKph (1,1) double {mustBePositive} = 80
    options.Mu (1,1) double {mustBePositive} = 0.85
    options.StopTimeS (1,1) double {mustBePositive} = 2.5
    options.PressureSeed (1,1) double {mustBeInteger} = 20260607
    options.OutputCsv (1,1) string = fullfile("data", "carsim_dataset_smoke.csv")
    options.SummaryJson (1,1) string = fullfile("results", "carsim_dataset_smoke_summary.json")
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "src"));
addpath(fullfile(projectRoot, "scripts"));

simFilePath = absoluteProjectPath(projectRoot, options.SimFilePath);
if ~isfile(simFilePath)
    error("CarSim:MissingSimFile", ...
        "CarSim sim file not found: %s", simFilePath);
end

manifest = table( ...
    1, options.InitialSpeedKph, options.Mu, 1, ...
    options.PressureSeed, options.StopTimeS, simFilePath, ...
    VariableNames=[ ...
        "case_id", "initial_speed_kph", "mu", "replicate", ...
        "pressure_seed", "stop_time_s", "run_file"]);

dataset = carsim_collect_dataset( ...
    manifest, options.OutputCsv, ...
    ModelPath=options.ModelPath, ...
    RunFileDialogParameter="SIMFILE", ...
    FailOnSpeedMismatch=true, ...
    SaveRawOutputs=false);

requiredColumns = [ ...
    "trajectory_id", "step", "time_s", "v_mps", "a_mps2", ...
    "pressure_MPa", "mu", "v_next_mps", "a_next_mps2", ...
    "initial_speed_kph", "source"];
columnsOk = all(ismember(requiredColumns, ...
    string(dataset.Properties.VariableNames)));
finiteColumns = [ ...
    "time_s", "v_mps", "a_mps2", "pressure_MPa", "mu", ...
    "v_next_mps", "a_next_mps2"];
finiteOutputOk = true;
for column = finiteColumns
    finiteOutputOk = finiteOutputOk && ...
        all(isfinite(dataset.(column)));
end

cfg = defaultCarSimConfig(projectRoot);
timeStep = diff(dataset.time_s);
sampleStepOk = ~isempty(timeStep) && ...
    max(abs(timeStep - cfg.datasetStepS)) < 1e-9;
transitionSpeedOk = all(dataset.v_next_mps >= -1e-9);
pressureExcitedOk = max(dataset.pressure_MPa) > 0.1;
speedResponseOk = dataset.v_next_mps(end) < dataset.v_mps(1);
muOk = all(abs(dataset.mu - options.Mu) < 1e-12);
sourceOk = all(string(dataset.source) == "CarSim");

summary = struct();
summary.passed = columnsOk && finiteOutputOk && sampleStepOk && ...
    transitionSpeedOk && pressureExcitedOk && speedResponseOk && ...
    muOk && sourceOk;
summary.rowCount = height(dataset);
summary.trajectoryCount = numel(unique(dataset.trajectory_id));
summary.sampleStepS = median(timeStep);
summary.initialSpeedKph = dataset.v_mps(1) * 3.6;
summary.finalSpeedKph = dataset.v_next_mps(end) * 3.6;
summary.maximumPressureMPa = max(dataset.pressure_MPa);
summary.minimumAccelerationMps2 = min(dataset.a_next_mps2);
summary.columnsOk = columnsOk;
summary.finiteOutputOk = finiteOutputOk;
summary.sampleStepOk = sampleStepOk;
summary.transitionSpeedOk = transitionSpeedOk;
summary.pressureExcitedOk = pressureExcitedOk;
summary.speedResponseOk = speedResponseOk;
summary.muOk = muOk;
summary.sourceOk = sourceOk;

writeJsonWithFolder(summary, ...
    absoluteProjectPath(projectRoot, options.SummaryJson));

fprintf("\nCarSim dataset collector verification\n");
fprintf("  rows:             %d\n", summary.rowCount);
fprintf("  sample step:      %.6f s\n", summary.sampleStepS);
fprintf("  initial speed:    %.3f km/h\n", summary.initialSpeedKph);
fprintf("  final speed:      %.3f km/h\n", summary.finalSpeedKph);
fprintf("  maximum pressure: %.3f MPa\n", summary.maximumPressureMPa);
fprintf("  minimum accel:    %.3f m/s^2\n", summary.minimumAccelerationMps2);
fprintf("  result:           %s\n", passFail(summary.passed));

if ~summary.passed
    error("CarSim:DatasetSmokeVerificationFailed", ...
        "CarSim collector ran, but one or more dataset checks failed.");
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

function writeJsonWithFolder(data, pathValue)
folder = fileparts(pathValue);
if strlength(folder) > 0 && ~isfolder(folder)
    mkdir(folder);
end
fileId = fopen(pathValue, "w");
if fileId < 0
    error("CarSim:SummaryWriteFailed", ...
        "Unable to write summary: %s", pathValue);
end
cleanup = onCleanup(@() fclose(fileId));
fprintf(fileId, "%s", jsonencode(data, PrettyPrint=true));
end

function text = passFail(value)
if value
    text = "PASS";
else
    text = "FAIL";
end
end

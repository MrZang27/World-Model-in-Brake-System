function report = verify_carsim_cosim_smoke(options)
%VERIFY_CARSIM_COSIM_SMOKE Run one real CarSim/Simulink braking case.

arguments
    options.ModelPath (1,1) string = fullfile("models", "carsim_brake_cosim.slx")
    options.SimFilePath (1,1) string = ""
    options.PressureMPa (1,1) double {mustBeNonnegative} = 2.0
    options.StopTimeS (1,1) double {mustBePositive} = 2.5
    options.ExpectedInitialSpeedKph (1,1) double {mustBeNonnegative} = 80
    options.ExpectedMu (1,1) double {mustBeNonnegative} = 0.85
    options.SpeedToleranceKph (1,1) double {mustBePositive} = 5
    options.OutputCsv (1,1) string = fullfile("results", "carsim_smoke_trajectory.csv")
    options.SummaryJson (1,1) string = fullfile("results", "carsim_smoke_summary.json")
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "src"));
addpath(fullfile(projectRoot, "scripts"));

modelPath = absoluteProjectPath(projectRoot, options.ModelPath);
if ~isfile(modelPath)
    error("CarSim:MissingModel", ...
        "Co-simulation model not found: %s", modelPath);
end

[~, modelName] = fileparts(modelPath);
blockPath = modelName + "/CarSimVehicle";
wasLoaded = bdIsLoaded(modelName);
load_system(modelPath);
cleanup = onCleanup(@() closeIfNeeded(modelName, wasLoaded));

if ~isempty(options.SimFilePath)
    simFilePath = absoluteProjectPath(projectRoot, options.SimFilePath);
    if ~isfile(simFilePath)
        error("CarSim:MissingSimFile", ...
            "CarSim sim file not found: %s", simFilePath);
    end
    set_param(blockPath, "SIMFILE", simFilePath);
else
    simFilePath = string(get_param(blockPath, "SIMFILE"));
end

if ~isfile(simFilePath)
    error("CarSim:MissingSimFile", ...
        "The CarSim block SIMFILE is not an existing file: %s", simFilePath);
end

pressureProfile = makePressureProfile( ...
    options.StopTimeS, options.PressureMPa);
workspaceCleanup = installTemporaryWorkspaceVariables( ...
    pressureProfile, options.ExpectedMu);

fprintf("Compiling %s with SIMFILE=%s\n", modelName, simFilePath);
set_param(modelName, "SimulationCommand", "update");
ports = get_param(blockPath, "Ports");
if ports(1) < 1 || ports(2) < 1
    error("CarSim:InvalidPorts", ...
        "VehicleSim S-Function does not expose input/output ports.");
end
solverType = string(get_param(modelName, "SolverType"));
solverName = string(get_param(modelName, "Solver"));
fixedStep = string(get_param(modelName, "FixedStep"));

simIn = Simulink.SimulationInput(modelName);
simIn = simIn.setVariable("case_pressure_profile", pressureProfile);
simIn = simIn.setVariable("case_mu", options.ExpectedMu);
simIn = simIn.setModelParameter( ...
    "StopTime", num2str(options.StopTimeS, "%.9g"));

fprintf("Running CarSim smoke case: %.1f km/h, mu=%.2f, P=%.2f MPa\n", ...
    options.ExpectedInitialSpeedKph, options.ExpectedMu, options.PressureMPa);
simOut = sim(simIn);

vSignal = getLoggedTimeseries(simOut, "v_carsim_ts");
aSignal = getLoggedTimeseries(simOut, "a_carsim_ts");
pSignal = getLoggedTimeseries(simOut, "pressure_command_ts");

time = double(vSignal.Time(:));
speedMps = double(vSignal.Data(:));
accelMps2 = interpSignal(aSignal, time);
pressureMPa = interpSignal(pSignal, time);

valid = isfinite(time) & isfinite(speedMps) & ...
    isfinite(accelMps2) & isfinite(pressureMPa);
time = time(valid);
speedMps = speedMps(valid);
accelMps2 = accelMps2(valid);
pressureMPa = pressureMPa(valid);
if numel(time) < 2
    error("CarSim:InsufficientOutput", ...
        "CarSim returned fewer than two finite output samples.");
end

initialSpeedKph = speedMps(1) * 3.6;
finalSpeedKph = speedMps(end) * 3.6;
speedDropKph = initialSpeedKph - finalSpeedKph;
minimumAccelMps2 = min(accelMps2);
maximumPressureMPa = max(pressureMPa);

initialSpeedOk = abs(initialSpeedKph - ...
    options.ExpectedInitialSpeedKph) <= options.SpeedToleranceKph;
pressureOk = maximumPressureMPa >= 0.8 * options.PressureMPa;
brakingResponseOk = speedDropKph > 0.2 && minimumAccelMps2 < -0.05;
finiteOutputOk = all(valid);
passed = initialSpeedOk && pressureOk && brakingResponseOk && finiteOutputOk;

trajectory = table( ...
    time, speedMps, accelMps2, pressureMPa, ...
    repmat(options.ExpectedMu, numel(time), 1), ...
    VariableNames=[ ...
        "time_s", "v_mps", "a_mps2", "pressure_MPa", "mu"]);
writeTableWithFolder(trajectory, absoluteProjectPath(projectRoot, options.OutputCsv));

report = struct();
report.passed = passed;
report.modelPath = modelPath;
report.simFilePath = simFilePath;
report.sampleCount = numel(time);
report.initialSpeedKph = initialSpeedKph;
report.finalSpeedKph = finalSpeedKph;
report.speedDropKph = speedDropKph;
report.minimumAccelMps2 = minimumAccelMps2;
report.maximumPressureMPa = maximumPressureMPa;
report.expectedMu = options.ExpectedMu;
report.solverType = solverType;
report.solverName = solverName;
report.fixedStep = fixedStep;
report.initialSpeedOk = initialSpeedOk;
report.pressureOk = pressureOk;
report.brakingResponseOk = brakingResponseOk;
report.finiteOutputOk = finiteOutputOk;
writeJsonWithFolder(report, ...
    absoluteProjectPath(projectRoot, options.SummaryJson));

fprintf("\nCarSim smoke verification\n");
fprintf("  samples:          %d\n", report.sampleCount);
fprintf("  initial speed:    %.3f km/h\n", report.initialSpeedKph);
fprintf("  final speed:      %.3f km/h\n", report.finalSpeedKph);
fprintf("  speed drop:       %.3f km/h\n", report.speedDropKph);
fprintf("  minimum accel:    %.3f m/s^2\n", report.minimumAccelMps2);
fprintf("  maximum pressure: %.3f MPa\n", report.maximumPressureMPa);
fprintf("  Simulink solver:  %s / %s (FixedStep=%s)\n", ...
    report.solverType, report.solverName, report.fixedStep);
fprintf("  result:           %s\n", passFail(report.passed));

if ~report.passed
    error("CarSim:SmokeVerificationFailed", ...
        "CarSim co-simulation ran, but one or more signal checks failed.");
end
clear workspaceCleanup;
end

function profile = makePressureProfile(stopTimeS, pressureMPa)
rampStart = min(0.5, 0.2 * stopTimeS);
rampEnd = min(rampStart + 0.1, 0.4 * stopTimeS);
releaseTime = max(rampEnd, stopTimeS - 0.2);
time = [0; rampStart; rampEnd; releaseTime; stopTimeS];
pressure = [0; 0; pressureMPa; pressureMPa; 0];
profile = timeseries(pressure, time);
end

function cleanup = installTemporaryWorkspaceVariables(pressureProfile, mu)
names = ["case_pressure_profile", "case_mu"];
values = {pressureProfile, mu};
oldExists = false(size(names));
oldValues = cell(size(names));

for i = 1:numel(names)
    oldExists(i) = evalin("base", ...
        "exist('" + names(i) + "', 'var') == 1");
    if oldExists(i)
        oldValues{i} = evalin("base", names(i));
    end
    assignin("base", names(i), values{i});
end

cleanup = onCleanup(@() restoreWorkspaceVariables( ...
    names, oldExists, oldValues));
end

function restoreWorkspaceVariables(names, oldExists, oldValues)
for i = 1:numel(names)
    if oldExists(i)
        assignin("base", names(i), oldValues{i});
    else
        evalin("base", "clear " + names(i));
    end
end
end

function signal = getLoggedTimeseries(simOut, name)
try
    signal = simOut.get(name);
catch
    signal = [];
end
if isempty(signal) || ~isa(signal, "timeseries")
    error("CarSim:MissingOutput", ...
        "Simulation output '%s' is missing or is not a timeseries.", name);
end
end

function values = interpSignal(signal, time)
signalTime = double(signal.Time(:));
signalData = double(signal.Data(:));
[signalTime, uniqueIndex] = unique(signalTime, "stable");
signalData = signalData(uniqueIndex);
if numel(signalTime) == 1
    values = repmat(signalData, size(time));
    return;
end
values = interp1(signalTime, signalData, time, "linear", "extrap");
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

function writeTableWithFolder(data, pathValue)
folder = fileparts(pathValue);
if strlength(folder) > 0 && ~isfolder(folder)
    mkdir(folder);
end
writetable(data, pathValue);
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

function closeIfNeeded(modelName, wasLoaded)
if ~wasLoaded && bdIsLoaded(modelName)
    close_system(modelName, 0);
end
end

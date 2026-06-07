function cases = prepare_carsim_batch_manifest(options)
%PREPARE_CARSIM_BATCH_MANIFEST Build a validated local CarSim case manifest.

arguments
    options.RunDirectory (1,1) string = fullfile("config", "carsim_runs")
    options.OutputCsv (1,1) string = fullfile("config", "carsim_case_manifest.local.csv")
    options.ReplicatesPerCondition (1,1) double ...
        {mustBeInteger, mustBePositive} = 5
    options.StopTimeS (1,1) double {mustBePositive} = 6.0
    options.Seed (1,1) double {mustBeInteger} = 41
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "scripts"));

validation = validate_carsim_run_library( ...
    RunDirectory=options.RunDirectory, ...
    FailOnInvalid=true);

runDirectory = absoluteProjectPath(projectRoot, options.RunDirectory);
outputCsv = absoluteProjectPath(projectRoot, options.OutputCsv);
cases = generate_carsim_case_manifest( ...
    outputCsv, ...
    ReplicatesPerCondition=options.ReplicatesPerCondition, ...
    StopTimeS=options.StopTimeS, ...
    Seed=options.Seed);

for i = 1:height(cases)
    fileName = sprintf("v%03d_mu%03d.sim", ...
        round(cases.initial_speed_kph(i)), round(100 * cases.mu(i)));
    runPath = fullfile(runDirectory, fileName);
    if ~isfile(runPath)
        error("CarSim:MissingConditionRun", ...
            "Missing CarSim Run for %.1f km/h, mu=%.2f: %s", ...
            cases.initial_speed_kph(i), cases.mu(i), runPath);
    end
    cases.run_file(i) = runPath;
end

writetable(cases, outputCsv);
fprintf("Prepared local CarSim batch manifest: %s\n", outputCsv);
fprintf("  validated Run files: %d\n", height(validation));
fprintf("  physical conditions: %d\n", ...
    height(unique(cases(:, ["initial_speed_kph", "mu"]))));
fprintf("  pressure trajectories: %d\n", height(cases));
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

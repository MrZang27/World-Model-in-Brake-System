function report = validate_carsim_run_library(options)
%VALIDATE_CARSIM_RUN_LIBRARY Validate named CarSim .sim run descriptors.

arguments
    options.RunDirectory (1,1) string = fullfile("config", "carsim_runs")
    options.OutputCsv (1,1) string = fullfile("results", "carsim_run_library_validation.csv")
    options.FailOnInvalid (1,1) logical = true
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
runDirectory = absoluteProjectPath(projectRoot, options.RunDirectory);
if ~isfolder(runDirectory)
    error("CarSim:MissingRunDirectory", ...
        "CarSim run directory not found: %s", runDirectory);
end

files = dir(fullfile(runDirectory, "v*_mu*.sim"));
if isempty(files)
    error("CarSim:NoRunFiles", ...
        "No vXXX_muXXX.sim files found in %s.", runDirectory);
end

n = numel(files);
file_name = strings(n, 1);
expected_speed_kph = nan(n, 1);
expected_mu = nan(n, 1);
root_file_name = strings(n, 1);
run_all_path = strings(n, 1);
run_all_exists = false(n, 1);
actual_speed_kph = nan(n, 1);
actual_mu = nan(n, 1);
ports_ok = false(n, 1);
step_ok = false(n, 1);

for i = 1:n
    file_name(i) = string(files(i).name);
    tokens = regexp(files(i).name, ...
        "^v(\d{3})_mu(\d{3})\.sim$", "tokens", "once");
    if isempty(tokens)
        continue;
    end
    expected_speed_kph(i) = str2double(tokens{1});
    expected_mu(i) = str2double(tokens{2}) / 100;

    simPath = fullfile(files(i).folder, files(i).name);
    simText = fileread(simPath);
    root_file_name(i) = firstToken(simText, ...
        "SET_MACRO\s+\$\(ROOT_FILE_NAME\)\$\s+([^\r\n]+)");
    workDirectory = firstToken(simText, ...
        "SET_MACRO\s+\$\(WORK_DIR\)\$\s+([^\r\n]+)");
    externalStep = str2double(firstToken(simText, ...
        "EXT_MODEL_STEP\s+([0-9.eE+-]+)"));
    importPorts = firstToken(simText, "PORTS_IMP\s+([^\r\n]+)");
    exportPorts = firstToken(simText, "PORTS_EXP\s+([^\r\n]+)");
    ports_ok(i) = importPorts == "1,4" && exportPorts == "1,2";
    step_ok(i) = isfinite(externalStep) && abs(externalStep - 0.001) < 1e-12;

    if strlength(root_file_name(i)) == 0 || strlength(workDirectory) == 0
        continue;
    end
    run_all_path(i) = fullfile(workDirectory, "Results", ...
        root_file_name(i), "Run_all.par");
    run_all_exists(i) = isfile(run_all_path(i));
    if ~run_all_exists(i)
        continue;
    end

    runText = fileread(run_all_path(i));
    actual_speed_kph(i) = lastNumericToken(runText, ...
        "SPEED_TARGET_CONSTANT\s+([0-9.eE+-]+)");
    actual_mu(i) = lastNumericToken(runText, ...
        "MU_ROAD_CONSTANT\s+([0-9.eE+-]+)");
end

root_unique = false(n, 1);
validRoots = root_file_name(strlength(root_file_name) > 0);
for i = 1:n
    if strlength(root_file_name(i)) > 0
        root_unique(i) = nnz(validRoots == root_file_name(i)) == 1;
    end
end

speed_match = abs(actual_speed_kph - expected_speed_kph) < 1e-6;
mu_match = abs(actual_mu - expected_mu) < 1e-6;
valid = run_all_exists & root_unique & speed_match & mu_match & ...
    ports_ok & step_ok;

report = table(file_name, expected_speed_kph, expected_mu, ...
    root_file_name, root_unique, run_all_path, run_all_exists, ...
    actual_speed_kph, actual_mu, speed_match, mu_match, ...
    ports_ok, step_ok, valid);
report = sortrows(report, ["expected_speed_kph", "expected_mu"]);

outputPath = absoluteProjectPath(projectRoot, options.OutputCsv);
outputFolder = fileparts(outputPath);
if strlength(outputFolder) > 0 && ~isfolder(outputFolder)
    mkdir(outputFolder);
end
writetable(report, outputPath);

fprintf("CarSim run-library validation\n");
fprintf("  files:             %d\n", height(report));
fprintf("  unique Run roots:  %d\n", numel(unique(validRoots)));
fprintf("  valid conditions:  %d\n", nnz(report.valid));
fprintf("  result:            %s\n", passFail(all(report.valid)));
fprintf("  report:            %s\n", outputPath);

if options.FailOnInvalid && ~all(report.valid)
    invalid = report(~report.valid, ...
        ["file_name", "root_file_name", "actual_speed_kph", ...
        "actual_mu", "root_unique", "speed_match", "mu_match"]);
    disp(invalid);
    error("CarSim:InvalidRunLibrary", ...
        "The CarSim run library contains duplicate or mismatched Run descriptors.");
end
end

function value = firstToken(text, pattern)
tokens = regexp(text, pattern, "tokens", "once");
if isempty(tokens)
    value = "";
else
    value = strip(string(tokens{1}));
end
end

function value = lastNumericToken(text, pattern)
tokens = regexp(text, pattern, "tokens");
if isempty(tokens)
    value = NaN;
else
    value = str2double(tokens{end}{1});
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

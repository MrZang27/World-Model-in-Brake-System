function dataset = carsim_collect_dataset_template(modelName, outCsv, numCases)
%CARSIM_COLLECT_DATASET_TEMPLATE Compatibility entry for the old template.
%
% The previous version only set MATLAB variables and could not guarantee
% that CarSim used the requested initial speed or road friction. The real
% workflow now uses a CarSim run manifest and carsim_collect_dataset.

if nargin < 1 || strlength(string(modelName)) == 0
    modelName = "carsim_brake_cosim";
end
if nargin < 2 || strlength(string(outCsv)) == 0
    outCsv = fullfile("data", "carsim_brake_sequence_dataset.csv");
end
if nargin < 3 || isempty(numCases)
    numCases = 24;
end

warning("CarSim:DeprecatedTemplate", ...
    "This compatibility function now creates a manifest template. " + ...
    "Fill its run_file column, then call carsim_collect_dataset.");

replicates = max(1, ceil(numCases / 24));
manifestPath = fullfile("config", "carsim_case_manifest.csv");
cases = generate_carsim_case_manifest(manifestPath, ...
    InitialSpeedsKph=[20 40 60 80 100 120], ...
    MuValues=[0.2 0.4 0.6 0.8], ...
    ReplicatesPerCondition=replicates);
cases = cases(1:min(numCases, height(cases)), :);
writetable(cases, manifestPath);

fprintf("Model requested: %s\n", modelName);
fprintf("Fill CarSim run files in: %s\n", manifestPath);
fprintf("Then run:\n");
fprintf('  carsim_collect_dataset("%s", "%s", ModelPath=fullfile("models", "%s.slx"))\n', ...
    manifestPath, outCsv, modelName);
dataset = table();
end


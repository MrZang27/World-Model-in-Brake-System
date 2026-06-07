function cases = generate_carsim_case_manifest(outCsv, options)
%GENERATE_CARSIM_CASE_MANIFEST Create a CarSim batch-run manifest template.
%
% Each unique speed/mu condition should point to a CarSim run file that was
% generated from a Run dataset with matching initial speed and road friction.
% Multiple pressure-profile replicates can share that run file.

arguments
    outCsv (1,1) string = fullfile("config", "carsim_case_manifest.csv")
    options.InitialSpeedsKph (1,:) double = [20 40 60 80 100 120]
    options.MuValues (1,:) double = [0.2 0.4 0.6 0.8]
    options.ReplicatesPerCondition (1,1) double {mustBeInteger, mustBePositive} = 5
    options.StopTimeS (1,1) double {mustBePositive} = 6.0
    options.Seed (1,1) double {mustBeInteger} = 41
end

[speedGrid, muGrid, replicateGrid] = ndgrid( ...
    options.InitialSpeedsKph, options.MuValues, ...
    1:options.ReplicatesPerCondition);

initial_speed_kph = speedGrid(:);
mu = muGrid(:);
replicate = replicateGrid(:);
n = numel(initial_speed_kph);
case_id = (1:n)';
pressure_seed = options.Seed + case_id;
stop_time_s = repmat(options.StopTimeS, n, 1);
run_file = strings(n, 1);

cases = table(case_id, initial_speed_kph, mu, replicate, pressure_seed, ...
    stop_time_s, run_file);

outDir = fileparts(outCsv);
if strlength(outDir) > 0 && ~isfolder(outDir)
    mkdir(outDir);
end
writetable(cases, outCsv);
fprintf("Saved CarSim case manifest template: %s\n", outCsv);
fprintf("Fill run_file for each speed/mu condition before batch collection.\n");
end


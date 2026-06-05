function dataset = carsim_collect_dataset_template(modelName, outCsv, numCases)
%CARSIM_COLLECT_DATASET_TEMPLATE Batch-collect CarSim/Simulink brake data.
%
% Before running this template, configure the Simulink model so it reads:
%   case_initial_speed_kph, case_mu, case_pressure_time_s, case_pressure_MPa
% and logs these signals to logsout:
%   v_mps, a_mps2, pressure_MPa, mu
%
% Example:
%   dataset = carsim_collect_dataset_template("carsim_brake_model", ...
%       fullfile("data", "carsim_brake_sequence_dataset.csv"), 200);

if nargin < 1 || strlength(string(modelName)) == 0
    error("Provide the Simulink model name that wraps the CarSim S-Function.");
end
if nargin < 2 || strlength(string(outCsv)) == 0
    outCsv = fullfile("data", "carsim_brake_sequence_dataset.csv");
end
if nargin < 3 || isempty(numCases)
    numCases = 200;
end

cases = sampleBrakeCases(numCases);
tables = cell(numCases, 1);

for i = 1:numCases
    pressureProfile = makePressureProfile(cases.initial_speed_kph(i), cases.mu(i));

    simIn = Simulink.SimulationInput(modelName);
    simIn = simIn.setVariable("case_initial_speed_kph", cases.initial_speed_kph(i));
    simIn = simIn.setVariable("case_mu", cases.mu(i));
    simIn = simIn.setVariable("case_pressure_time_s", pressureProfile.time_s);
    simIn = simIn.setVariable("case_pressure_MPa", pressureProfile.pressure_MPa);

    simOut = sim(simIn);
    tables{i} = extractTrajectoryTable(simOut, i);
end

dataset = vertcat(tables{:});
outDir = fileparts(outCsv);
if strlength(string(outDir)) > 0 && ~exist(outDir, "dir")
    mkdir(outDir);
end
writetable(dataset, outCsv);
fprintf("Saved CarSim sequence dataset: %s\n", outCsv);
end

function cases = sampleBrakeCases(numCases)
rng(31);
initialSpeedKph = 20 + (120 - 20) * rand(numCases, 1);
mu = 0.2 + (0.8 - 0.2) * rand(numCases, 1);
cases = table(initialSpeedKph, mu, 'VariableNames', {'initial_speed_kph', 'mu'});
end

function profile = makePressureProfile(~, ~)
dt = 0.05;
tEnd = 6.0;
time = (0:dt:tEnd)';
pressure = zeros(size(time));
target = 10 * rand();
for k = 2:numel(time)
    if mod(k, randi([15, 35])) == 1
        target = 10 * rand();
    end
    pressure(k) = min(max(0.88 * pressure(k - 1) + 0.12 * target + 0.18 * randn(), 0), 10);
end
profile = table(time, pressure, 'VariableNames', {'time_s', 'pressure_MPa'});
end

function tbl = extractTrajectoryTable(simOut, trajectoryId)
logs = simOut.logsout;
vSig = signalData(logs, "v_mps");
aSig = signalData(logs, "a_mps2");
pSig = signalData(logs, "pressure_MPa");
muSig = signalData(logs, "mu");

t = vSig.Time(:);
v = vSig.Data(:);
a = interp1(aSig.Time(:), aSig.Data(:), t, "linear", "extrap");
pressure = interp1(pSig.Time(:), pSig.Data(:), t, "linear", "extrap");
mu = interp1(muSig.Time(:), muSig.Data(:), t, "previous", "extrap");

n = numel(t) - 1;
trajectory_id = repmat(trajectoryId, n, 1);
step = (0:n-1)';
time_s = t(1:n);
v_mps = v(1:n);
a_mps2 = a(1:n);
pressure_MPa = pressure(1:n);
mu_t = mu(1:n);
v_next_mps = v(2:n+1);
a_next_mps2 = a(2:n+1);

tbl = table(trajectory_id, step, time_s, v_mps, a_mps2, pressure_MPa, mu_t, ...
    v_next_mps, a_next_mps2, ...
    'VariableNames', {'trajectory_id', 'step', 'time_s', 'v_mps', 'a_mps2', ...
    'pressure_MPa', 'mu', 'v_next_mps', 'a_next_mps2'});
end

function values = signalData(logs, name)
element = logs.get(name);
if isempty(element)
    error("Missing logsout signal '%s'. Update the signal name mapping in this template.", name);
end
values = element.Values;
end


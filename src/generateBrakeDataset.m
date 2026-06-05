function data = generateBrakeDataset(numSamples, outCsv)
%GENERATEBRAKEDATASET Generate pseudo-real transition data from mechanism model.

if nargin < 1 || isempty(numSamples)
    numSamples = 30000;
end
if nargin < 2
    outCsv = "";
end

p = defaultBrakeParams();
rng(7);

v = (10 + (120 - 10) * rand(numSamples, 1)) / 3.6;
a = -8 * rand(numSamples, 1);
pressure = 10 * rand(numSamples, 1);
muChoices = [0.2; 0.4; 0.6; 0.8];
mu = muChoices(randi(numel(muChoices), numSamples, 1));

next = zeros(numSamples, 2);
slipRisk = false(numSamples, 1);
utilization = zeros(numSamples, 1);

for i = 1:numSamples
    [next(i, :), info] = brakeStep([v(i), a(i)], pressure(i), mu(i), p);
    slipRisk(i) = info.slipRisk;
    utilization(i) = info.utilization;
end

data.X = [v, a, pressure, mu];
data.Y = next;
data.table = table(v, a, pressure, mu, next(:, 1), next(:, 2), utilization, slipRisk, ...
    'VariableNames', {'v_mps', 'a_mps2', 'pressure_MPa', 'mu', 'v_next_mps', ...
    'a_next_mps2', 'brake_utilization', 'slip_risk'});

if strlength(outCsv) > 0
    writetable(data.table, outCsv);
end
end

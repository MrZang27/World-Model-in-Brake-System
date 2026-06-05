function data = generateBrakeSequenceDataset(numTraj, stepsPerTraj, outCsv)
%GENERATEBRAKESEQUENCEDATASET Generate trajectory data for sequence models.
%
% The generated CSV keeps the same state/action/next-state columns as the
% one-step dataset, with trajectory_id and step added for LSTM/GRU training.

if nargin < 1 || isempty(numTraj)
    numTraj = 800;
end
if nargin < 2 || isempty(stepsPerTraj)
    stepsPerTraj = 120;
end
if nargin < 3
    outCsv = "";
end

p = defaultBrakeParams();
rng(19);

n = numTraj * stepsPerTraj;
trajectoryId = zeros(n, 1);
step = zeros(n, 1);
time = zeros(n, 1);
v = zeros(n, 1);
a = zeros(n, 1);
pressure = zeros(n, 1);
mu = zeros(n, 1);
vNext = zeros(n, 1);
aNext = zeros(n, 1);
utilization = zeros(n, 1);
slipRisk = false(n, 1);

row = 0;
muChoices = [0.2; 0.4; 0.6; 0.8];

for traj = 1:numTraj
    state = [(20 + (120 - 20) * rand()) / 3.6, 0];
    baseMu = muChoices(randi(numel(muChoices)));
    nextMu = muChoices(randi(numel(muChoices)));
    changeStep = randi([round(0.35 * stepsPerTraj), round(0.75 * stepsPerTraj)]);
    pressureNow = 10 * rand();
    pressureTarget = 10 * rand();

    for k = 1:stepsPerTraj
        row = row + 1;
        if mod(k, randi([12, 28])) == 1
            pressureTarget = 10 * rand();
        end
        pressureNow = min(max(0.86 * pressureNow + 0.14 * pressureTarget + 0.25 * randn(), 0), 10);
        muNow = baseMu;
        if k >= changeStep
            muNow = nextMu;
        end

        [nextState, info] = brakeStep(state, pressureNow, muNow, p);

        trajectoryId(row) = traj;
        step(row) = k - 1;
        time(row) = (k - 1) * p.dt;
        v(row) = state(1);
        a(row) = state(2);
        pressure(row) = pressureNow;
        mu(row) = muNow;
        vNext(row) = nextState(1);
        aNext(row) = nextState(2);
        utilization(row) = info.utilization;
        slipRisk(row) = info.slipRisk;

        state = nextState;
    end
end

data.X = [v, a, pressure, mu];
data.Y = [vNext, aNext];
data.table = table(trajectoryId, step, time, v, a, pressure, mu, vNext, aNext, utilization, slipRisk, ...
    'VariableNames', {'trajectory_id', 'step', 'time_s', 'v_mps', 'a_mps2', 'pressure_MPa', ...
    'mu', 'v_next_mps', 'a_next_mps2', 'brake_utilization', 'slip_risk'});

if strlength(outCsv) > 0
    writetable(data.table, outCsv);
end
end


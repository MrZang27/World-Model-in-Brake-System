function [pressure, diagnostics] = selectSafeBrakePressure(model, state, targetSpeed, mu, p, candidates)
%SELECTSAFEBRAKEPRESSURE Evaluate candidate actions with the world model.

if nargin < 6 || isempty(candidates)
    candidates = 0:0.5:10;
end

n = numel(candidates);
X = [repmat(state, n, 1), candidates(:), repmat(mu, n, 1)];
pred = predictWorldModel(model, X);

fBrake = p.kBrake * candidates(:);
fMax = mu * p.m * p.g;
utilization = fBrake ./ max(fMax, eps);
decel = -pred(:, 2);

safe = utilization <= p.slipPressureRatio & decel <= min(mu * p.g, p.maxComfortDecel) + 0.25;
speedError = abs(pred(:, 1) - targetSpeed);
score = speedError + 20 * (~safe) + 0.02 * candidates(:);

[~, bestIdx] = min(score);
pressure = candidates(bestIdx);

diagnostics = struct();
diagnostics.candidates = candidates(:);
diagnostics.prediction = pred;
diagnostics.utilization = utilization;
diagnostics.safe = safe;
diagnostics.score = score;
end

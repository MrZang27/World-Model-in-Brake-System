function result = simulateSafetyScenario(model)
%SIMULATESAFETYSCENARIO Compare fixed braking with world-model safety shield.

p = defaultBrakeParams();
tEnd = 5;
t = (0:p.dt:tEnd)';
n = numel(t);
targetSpeed = 20 / 3.6;

mu = 0.8 * ones(n, 1);
mu(t >= 2.0) = 0.2;

stateFixed = zeros(n, 2);
stateShield = zeros(n, 2);
pressureFixed = 8 * ones(n, 1);
pressureShield = zeros(n, 1);
riskFixed = false(n, 1);
riskShield = false(n, 1);
predShield = zeros(n, 2);

stateFixed(1, :) = [80 / 3.6, 0];
stateShield(1, :) = [80 / 3.6, 0];

for k = 1:n-1
    [stateFixed(k + 1, :), infoFixed] = brakeStep(stateFixed(k, :), pressureFixed(k), mu(k), p);
    riskFixed(k) = infoFixed.slipRisk;

    [pressureShield(k), diag] = selectSafeBrakePressure(model, stateShield(k, :), targetSpeed, mu(k), p, 0:0.5:10);
    predShield(k, :) = diag.prediction(diag.candidates == pressureShield(k), :);
    [stateShield(k + 1, :), infoShield] = brakeStep(stateShield(k, :), pressureShield(k), mu(k), p);
    riskShield(k) = infoShield.slipRisk;
end
pressureShield(end) = pressureShield(end - 1);
predShield(end, :) = predShield(end - 1, :);

result = table(t, mu, pressureFixed, pressureShield, ...
    stateFixed(:, 1), stateShield(:, 1), stateFixed(:, 2), stateShield(:, 2), ...
    predShield(:, 1), predShield(:, 2), riskFixed, riskShield, ...
    'VariableNames', {'time_s', 'mu', 'pressure_fixed_MPa', 'pressure_shield_MPa', ...
    'v_fixed_mps', 'v_shield_mps', 'a_fixed_mps2', 'a_shield_mps2', ...
    'v_pred_shield_mps', 'a_pred_shield_mps2', 'risk_fixed', 'risk_shield'});
end

function plotClosedLoopResults(data, history, metrics, scenario, outDir)
%PLOTCLOSEDLOOPRESULTS Save main experiment figures.

if ~exist(outDir, 'dir')
    mkdir(outDir);
end

fig = figure('Name', 'Training Loss', 'Visible', 'off');
plot(history.trainLoss, 'LineWidth', 1.2);
hold on;
plot(history.valLoss, 'LineWidth', 1.2);
grid on;
xlabel('Epoch');
ylabel('Normalized MSE');
legend('Train', 'Validation', 'Location', 'northeast');
title('World Model Training Loss');
saveas(fig, fullfile(outDir, 'training_loss.png'));
close(fig);

sample = 1:min(800, size(data.Y, 1));
pred = metrics.prediction(sample, :);
fig = figure('Name', 'Prediction Compare', 'Visible', 'off');
tiledlayout(2, 1);
nexttile;
plot(data.Y(sample, 1), 'LineWidth', 1.0);
hold on;
plot(pred(:, 1), '--', 'LineWidth', 1.0);
grid on;
ylabel('v next (m/s)');
legend('Mechanism', 'World model');
nexttile;
plot(data.Y(sample, 2), 'LineWidth', 1.0);
hold on;
plot(pred(:, 2), '--', 'LineWidth', 1.0);
grid on;
ylabel('a next (m/s^2)');
xlabel('Sample');
legend('Mechanism', 'World model');
saveas(fig, fullfile(outDir, 'prediction_compare.png'));
close(fig);

fig = figure('Name', 'Road Adhesion Response', 'Visible', 'off');
muVals = [0.8, 0.4, 0.2];
press = 6;
v0 = 80 / 3.6;
for i = 1:numel(muVals)
    state = [v0, 0];
    acc = zeros(80, 1);
    for k = 1:80
        [state, ~] = brakeStep(state, press, muVals(i), defaultBrakeParams());
        acc(k) = state(2);
    end
    plot((0:79) * defaultBrakeParams().dt, acc, 'LineWidth', 1.2);
    hold on;
end
grid on;
xlabel('Time (s)');
ylabel('Acceleration (m/s^2)');
legend('mu=0.8 dry', 'mu=0.4 wet', 'mu=0.2 ice', 'Location', 'southeast');
title('Mechanism Response Under Different Road Adhesion');
saveas(fig, fullfile(outDir, 'mu_response.png'));
close(fig);

fig = figure('Name', 'Safety Planning Scenario', 'Visible', 'off');
tiledlayout(4, 1);
nexttile;
plot(scenario.time_s, scenario.mu, 'LineWidth', 1.2);
grid on;
ylabel('mu');
nexttile;
plot(scenario.time_s, scenario.pressure_fixed_MPa, 'LineWidth', 1.1);
hold on;
plot(scenario.time_s, scenario.pressure_shield_MPa, 'LineWidth', 1.1);
grid on;
ylabel('P (MPa)');
legend('Fixed', 'Shield');
nexttile;
plot(scenario.time_s, scenario.a_fixed_mps2, 'LineWidth', 1.1);
hold on;
plot(scenario.time_s, scenario.a_shield_mps2, 'LineWidth', 1.1);
plot(scenario.time_s, scenario.a_pred_shield_mps2, '--', 'LineWidth', 1.0);
grid on;
ylabel('a (m/s^2)');
legend('Fixed true', 'Shield true', 'Shield predicted');
nexttile;
stairs(scenario.time_s, scenario.risk_fixed, 'LineWidth', 1.1);
hold on;
stairs(scenario.time_s, scenario.risk_shield, 'LineWidth', 1.1);
grid on;
ylabel('Risk');
xlabel('Time (s)');
legend('Fixed', 'Shield');
saveas(fig, fullfile(outDir, 'safety_planning_scenario.png'));
close(fig);
end

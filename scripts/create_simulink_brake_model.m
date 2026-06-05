function create_simulink_brake_model()
%CREATE_SIMULINK_BRAKE_MODEL Build a visual Simulink mechanism model.

if isempty(ver('simulink'))
    warning('Simulink is not available. Skipping model generation.');
    return;
end

model = 'brake_mechanism_model';
outDir = fullfile(pwd, 'models');
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

if bdIsLoaded(model)
    close_system(model, 0);
end
modelPath = fullfile(outDir, [model '.slx']);
if exist(modelPath, 'file')
    delete(modelPath);
end

new_system(model);
open_system(model);
set_param(model, 'StopTime', '5', 'Solver', 'ode4', 'FixedStep', '0.05');

add_block('simulink/Sources/In1', [model '/v_t'], 'Position', [60 70 90 90]);
add_block('simulink/Sources/In1', [model '/P_MPa'], 'Position', [60 150 90 170]);
add_block('simulink/Sources/In1', [model '/mu'], 'Position', [60 230 90 250]);
add_block('simulink/User-Defined Functions/MATLAB Function', [model '/BrakeMechanism'], ...
    'Position', [210 95 390 235]);
add_block('simulink/Sinks/Out1', [model '/v_next'], 'Position', [520 125 550 145]);
add_block('simulink/Sinks/Out1', [model '/a_next'], 'Position', [520 185 550 205]);

rt = sfroot;
chart = rt.find('-isa', 'Stateflow.EMChart', 'Path', [model '/BrakeMechanism']);
chart.Script = sprintf([ ...
    'function [v_next,a_next] = BrakeMechanism(v_t,P_MPa,mu)\n', ...
    '%%#codegen\n', ...
    'm = 1800; g = 9.81; kBrake = 3500; dt = 0.05;\n', ...
    'fBrake = max(P_MPa,0) * kBrake;\n', ...
    'fMax = max(mu,0.01) * m * g;\n', ...
    'fActual = min(fBrake, fMax);\n', ...
    'a_next = -fActual / m;\n', ...
    'v_next = max(v_t + a_next * dt, 0);\n', ...
    'end\n']);

set_param(model, 'SimulationCommand', 'update');

add_line(model, 'v_t/1', 'BrakeMechanism/1', 'autorouting', 'on');
add_line(model, 'P_MPa/1', 'BrakeMechanism/2', 'autorouting', 'on');
add_line(model, 'mu/1', 'BrakeMechanism/3', 'autorouting', 'on');
add_line(model, 'BrakeMechanism/1', 'v_next/1', 'autorouting', 'on');
add_line(model, 'BrakeMechanism/2', 'a_next/1', 'autorouting', 'on');

save_system(model, modelPath);
close_system(model, 0);
fprintf('Generated Simulink model: %s\n', modelPath);
end

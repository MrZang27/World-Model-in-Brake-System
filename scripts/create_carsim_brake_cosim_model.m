function info = create_carsim_brake_cosim_model(seedModelPath, options)
%CREATE_CARSIM_BRAKE_COSIM_MODEL Build the project CarSim co-simulation model.
%
% First configure a CarSim Run with:
%   Imports: IMP_PBK_L1, IMP_PBK_L2, IMP_PBK_R1, IMP_PBK_R2
%   Exports: Vx_SM, Ax_SM
% Then use CarSim "Send to Simulink" and save that model as the seed model.
% This function copies the run-specific VehicleSim S-Function and adds the
% pressure source, unit conversions, and logging needed by this project.

arguments
    seedModelPath (1,1) string
    options.OutputModelPath (1,1) string = ""
    options.CarSimBlock (1,1) string = ""
    options.Overwrite (1,1) logical = false
end

if isempty(ver("simulink"))
    error("CarSim:NoSimulink", "Simulink is required.");
end
if ~isfile(seedModelPath)
    error("CarSim:MissingSeedModel", ...
        "Seed model not found: %s. Use CarSim 'Send to Simulink' first.", seedModelPath);
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cfg = defaultCarSimConfig(projectRoot);
if strlength(options.OutputModelPath) == 0
    outputModelPath = cfg.modelPath;
else
    outputModelPath = options.OutputModelPath;
end

[outputDir, targetModel] = fileparts(outputModelPath);
if ~isfolder(outputDir)
    mkdir(outputDir);
end
if isfile(outputModelPath) && ~options.Overwrite
    error("CarSim:OutputExists", ...
        "Output model already exists: %s. Set Overwrite=true to replace it.", outputModelPath);
end

[~, seedModel] = fileparts(seedModelPath);
seedWasLoaded = bdIsLoaded(seedModel);
load_system(seedModelPath);
seedCleanup = onCleanup(@() closeIfNeeded(seedModel, seedWasLoaded));

if strlength(options.CarSimBlock) > 0
    sourceBlock = options.CarSimBlock;
else
    sourceBlock = findCarSimBlock(seedModel);
end

if bdIsLoaded(targetModel)
    close_system(targetModel, 0);
end
if isfile(outputModelPath)
    delete(outputModelPath);
end

new_system(targetModel);
targetCleanup = onCleanup(@() closeIfNeeded(targetModel, false));
seedSolverType = string(get_param(seedModel, "SolverType"));
seedSolver = string(get_param(seedModel, "Solver"));
seedFixedStep = string(get_param(seedModel, "FixedStep"));
if strlength(seedFixedStep) == 0
    seedFixedStep = num2str(cfg.carSimStepS, "%.9g");
end
set_param(targetModel, ...
    "SolverType", seedSolverType, ...
    "Solver", seedSolver, ...
    "FixedStep", seedFixedStep, ...
    "StopTime", num2str(cfg.defaultStopTimeS, "%.9g"), ...
    "ReturnWorkspaceOutputs", "on", ...
    "SignalLogging", "off");
copyModelCallbacks(seedModel, targetModel);
copyModelWorkspace(seedModel, targetModel);

carSimBlock = targetModel + "/CarSimVehicle";
add_block(sourceBlock, carSimBlock, "Position", [485 205 685 335]);

add_block("simulink/Sources/From Workspace", targetModel + "/PressureProfile", ...
    "VariableName", "case_pressure_profile", ...
    "Interpolate", "on", ...
    "OutputAfterFinalValue", "Holding final value", ...
    "Position", [45 95 185 125]);
add_block("simulink/Discontinuities/Saturation", targetModel + "/PressureLimit", ...
    "UpperLimit", num2str(cfg.pressureMaxMPa), ...
    "LowerLimit", num2str(cfg.pressureMinMPa), ...
    "Position", [225 92 275 128]);
add_block("simulink/Math Operations/Gain", targetModel + "/PressureUnitScale", ...
    "Gain", num2str(cfg.pressureToCarSim, "%.12g"), ...
    "Position", [310 92 385 128]);
add_block("simulink/Signal Routing/Mux", targetModel + "/FourWheelPressure", ...
    "Inputs", "4", ...
    "Position", [430 70 435 175]);

add_block("simulink/Signal Routing/Demux", targetModel + "/CarSimExports", ...
    "Outputs", num2str(numel(cfg.exportVariables)), ...
    "Position", [740 205 745 335]);
add_block("simulink/Math Operations/Gain", targetModel + "/SpeedToMps", ...
    "Gain", num2str(cfg.speedToMps, "%.12g"), ...
    "Position", [795 205 875 235]);
add_block("simulink/Math Operations/Gain", targetModel + "/AccelToMps2", ...
    "Gain", num2str(cfg.accelToMps2, "%.12g"), ...
    "Position", [795 280 875 310]);

addTimeseriesSink(targetModel, "LogSpeed", "v_carsim_ts", [935 202 1055 238]);
addTimeseriesSink(targetModel, "LogAcceleration", "a_carsim_ts", [935 277 1055 313]);
addTimeseriesSink(targetModel, "LogPressure", "pressure_command_ts", [310 25 455 55]);

add_block("simulink/Sources/Constant", targetModel + "/CaseMu", ...
    "Value", "case_mu", ...
    "Position", [55 400 115 430]);
addTimeseriesSink(targetModel, "LogMu", "mu_case_ts", [180 397 300 433]);

add_line(targetModel, "PressureProfile/1", "PressureLimit/1", "autorouting", "on");
add_line(targetModel, "PressureLimit/1", "PressureUnitScale/1", "autorouting", "on");
for port = 1:4
    add_line(targetModel, "PressureUnitScale/1", ...
        "FourWheelPressure/" + string(port), "autorouting", "on");
end
add_line(targetModel, "PressureLimit/1", "LogPressure/1", "autorouting", "on");
add_line(targetModel, "FourWheelPressure/1", "CarSimVehicle/1", "autorouting", "on");
add_line(targetModel, "CarSimVehicle/1", "CarSimExports/1", "autorouting", "on");
add_line(targetModel, ...
    "CarSimExports/" + string(cfg.speedExportIndex), ...
    "SpeedToMps/1", "autorouting", "on");
add_line(targetModel, ...
    "CarSimExports/" + string(cfg.accelExportIndex), ...
    "AccelToMps2/1", "autorouting", "on");
add_line(targetModel, "SpeedToMps/1", "LogSpeed/1", "autorouting", "on");
add_line(targetModel, "AccelToMps2/1", "LogAcceleration/1", "autorouting", "on");
add_line(targetModel, "CaseMu/1", "LogMu/1", "autorouting", "on");

workspaceCleanup = installTemporaryWorkspaceVariables(cfg);
set_param(targetModel, "SimulationCommand", "update");
ports = get_param(carSimBlock, "Ports");
if ports(1) < 1 || ports(2) < 1
    error("CarSim:InvalidPorts", ...
        "The copied VehicleSim block does not expose import/export ports.");
end

save_system(targetModel, outputModelPath);
clear workspaceCleanup;

info = struct();
info.modelPath = string(outputModelPath);
info.carSimBlockPath = string(carSimBlock);
info.sourceBlockPath = string(sourceBlock);
info.importVariables = cfg.importVariables;
info.exportVariables = cfg.exportVariables;
fprintf("Generated CarSim co-simulation model: %s\n", outputModelPath);
fprintf("Imports must be: %s\n", strjoin(cfg.importVariables, ", "));
fprintf("Exports must be: %s\n", strjoin(cfg.exportVariables, ", "));
end

function cleanup = installTemporaryWorkspaceVariables(cfg)
names = ["case_pressure_profile", "case_mu"];
oldExists = false(size(names));
oldValues = cell(size(names));
for i = 1:numel(names)
    oldExists(i) = evalin("base", "exist('" + names(i) + "', 'var') == 1");
    if oldExists(i)
        oldValues{i} = evalin("base", names(i));
    end
end

assignin("base", "case_pressure_profile", ...
    timeseries([0; 0], [0; cfg.defaultStopTimeS]));
assignin("base", "case_mu", 0.8);
cleanup = onCleanup(@() restoreWorkspaceVariables(names, oldExists, oldValues));
end

function restoreWorkspaceVariables(names, oldExists, oldValues)
for i = 1:numel(names)
    if oldExists(i)
        assignin("base", names(i), oldValues{i});
    else
        evalin("base", "clear " + names(i));
    end
end
end

function block = findCarSimBlock(modelName)
blocks = find_system(modelName, "LookUnderMasks", "all", ...
    "FollowLinks", "on", "BlockType", "S-Function");
matches = strings(0, 1);
for i = 1:numel(blocks)
    functionName = string(get_param(blocks{i}, "FunctionName"));
    maskType = string(get_param(blocks{i}, "MaskType"));
    if any(contains(lower(functionName), ["vs_sf", "vehiclesim"])) || ...
            any(contains(lower(maskType), ["carsim", "vehiclesim"]))
        matches(end + 1, 1) = string(blocks{i}); %#ok<AGROW>
    end
end
if isempty(matches)
    error("CarSim:BlockNotFound", ...
        "No VehicleSim/CarSim S-Function was found in the seed model.");
end
if numel(matches) > 1
    error("CarSim:MultipleBlocks", ...
        "Multiple CarSim blocks found. Pass the desired path with CarSimBlock=...");
end
block = matches(1);
end

function addTimeseriesSink(modelName, blockName, variableName, position)
add_block("simulink/Sinks/To Workspace", modelName + "/" + blockName, ...
    "VariableName", variableName, ...
    "SaveFormat", "Timeseries", ...
    "MaxDataPoints", "inf", ...
    "Position", position);
end

function copyModelCallbacks(sourceModel, targetModel)
callbacks = ["PreLoadFcn", "PostLoadFcn", "InitFcn", "StartFcn", ...
    "StopFcn", "CloseFcn"];
for callback = callbacks
    try
        set_param(targetModel, callback, get_param(sourceModel, callback));
    catch
        % Some releases do not expose every callback as a writable property.
    end
end
end

function copyModelWorkspace(sourceModel, targetModel)
sourceWorkspace = get_param(sourceModel, "ModelWorkspace");
targetWorkspace = get_param(targetModel, "ModelWorkspace");
variables = whos(sourceWorkspace);
for i = 1:numel(variables)
    name = variables(i).name;
    assignin(targetWorkspace, name, getVariable(sourceWorkspace, name));
end
end

function closeIfNeeded(modelName, wasLoaded)
if ~wasLoaded && bdIsLoaded(modelName)
    close_system(modelName, 0);
end
end

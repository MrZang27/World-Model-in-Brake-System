function report = inspect_carsim_interface(modelPath, outTxt)
%INSPECT_CARSIM_INTERFACE Inspect a CarSim-generated Simulink seed model.
%
% Use this after CarSim "Send to Simulink". The report identifies the
% VehicleSim S-Function and lists its dialog parameters, which is useful
% when different CarSim run files must be selected from a batch script.

arguments
    modelPath (1,1) string
    outTxt (1,1) string = ""
end

if ~isfile(modelPath)
    error("CarSim:MissingSeedModel", ...
        "Seed model not found: %s. Use CarSim 'Send to Simulink' first.", modelPath);
end
if isempty(ver("simulink"))
    error("CarSim:NoSimulink", "Simulink is required.");
end

[~, modelName] = fileparts(modelPath);
wasLoaded = bdIsLoaded(modelName);
load_system(modelPath);
cleanup = onCleanup(@() closeIfNeeded(modelName, wasLoaded));

blocks = find_system(modelName, "LookUnderMasks", "all", ...
    "FollowLinks", "on", "BlockType", "S-Function");
isCarSim = false(size(blocks));
for i = 1:numel(blocks)
    functionName = string(get_param(blocks{i}, "FunctionName"));
    maskType = string(get_param(blocks{i}, "MaskType"));
    isCarSim(i) = any(contains(lower(functionName), ["vs_sf", "vehiclesim"])) || ...
        any(contains(lower(maskType), ["carsim", "vehiclesim"]));
end
blocks = string(blocks(isCarSim));

if isempty(blocks)
    error("CarSim:BlockNotFound", ...
        "No CarSim/VehicleSim S-Function was found in %s.", modelPath);
end

rows = {};
for i = 1:numel(blocks)
    block = blocks(i);
    rows(end + 1, :) = {"BLOCK", block, ""}; %#ok<AGROW>
    rows(end + 1, :) = {"FunctionName", string(get_param(block, "FunctionName")), ""}; %#ok<AGROW>
    rows(end + 1, :) = {"MaskType", string(get_param(block, "MaskType")), ""}; %#ok<AGROW>

    dialog = get_param(block, "DialogParameters");
    if ~isempty(dialog)
        names = string(fieldnames(dialog));
        for j = 1:numel(names)
            value = safeGetParam(block, names(j));
            rows(end + 1, :) = {"DialogParameter", names(j), value}; %#ok<AGROW>
        end
    end

    maskNames = string(get_param(block, "MaskNames"));
    maskValues = string(get_param(block, "MaskValues"));
    for j = 1:min(numel(maskNames), numel(maskValues))
        rows(end + 1, :) = {"MaskParameter", maskNames(j), maskValues(j)}; %#ok<AGROW>
    end
end

report = cell2table(rows, ...
    "VariableNames", ["item_type", "name", "value"]);
disp(report);

if strlength(outTxt) > 0
    outDir = fileparts(outTxt);
    if strlength(outDir) > 0 && ~isfolder(outDir)
        mkdir(outDir);
    end
    writetable(report, outTxt, "Delimiter", "\t", "FileType", "text");
    fprintf("Saved CarSim interface report: %s\n", outTxt);
end
end

function value = safeGetParam(block, name)
try
    raw = get_param(block, name);
    if isnumeric(raw) || islogical(raw)
        value = string(mat2str(raw));
    else
        value = string(raw);
    end
catch
    value = "<unavailable>";
end
end

function closeIfNeeded(modelName, wasLoaded)
if ~wasLoaded && bdIsLoaded(modelName)
    close_system(modelName, 0);
end
end

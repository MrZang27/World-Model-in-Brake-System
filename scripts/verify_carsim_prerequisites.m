function status = verify_carsim_prerequisites(seedModelPath)
%VERIFY_CARSIM_PREREQUISITES Check MATLAB, Simulink, and CarSim integration.

if nargin < 1
    seedModelPath = fullfile("models", "carsim_seed_model.slx");
end

status = struct();
status.simulinkAvailable = ~isempty(ver("simulink"));
status.vsSfLocation = string(which("vs_sf"));
status.vehicleSimSFunctionAvailable = strlength(status.vsSfLocation) > 0;
status.seedModelPath = string(seedModelPath);
status.seedModelExists = isfile(seedModelPath);

fprintf("Simulink available:          %s\n", yesNo(status.simulinkAvailable));
fprintf("VehicleSim vs_sf available: %s\n", ...
    yesNo(status.vehicleSimSFunctionAvailable));
if status.vehicleSimSFunctionAvailable
    fprintf("vs_sf location:              %s\n", status.vsSfLocation);
end
fprintf("Seed model exists:          %s\n", yesNo(status.seedModelExists));
fprintf("Seed model path:            %s\n", status.seedModelPath);

if ~status.simulinkAvailable
    warning("CarSim:NoSimulink", "Simulink is not available.");
end
if ~status.vehicleSimSFunctionAvailable
    warning("CarSim:NoVsSf", ...
        "The CarSim vs_sf S-Function is not on the MATLAB path. " + ...
        "Open the Run in CarSim and use 'Send to Simulink'.");
end
if ~status.seedModelExists
    warning("CarSim:NoSeedModel", ...
        "Save the CarSim-generated Simulink model as %s.", seedModelPath);
end
end

function text = yesNo(value)
if value
    text = "yes";
else
    text = "no";
end
end

function cfg = defaultCarSimConfig(projectRoot)
%DEFAULTCARSIMCONFIG Configuration shared by CarSim co-simulation tools.
%
% The CarSim seed model must expose one import-vector port and one
% export-vector port on its VehicleSim S-Function. Configure the CarSim
% Run with these channels in this exact order:
%   Imports: IMP_PBK_L1, IMP_PBK_L2, IMP_PBK_R1, IMP_PBK_R2
%   Exports: Vx_SM, Ax_SM

if nargin < 1 || strlength(string(projectRoot)) == 0
    projectRoot = fileparts(fileparts(mfilename('fullpath')));
end

p = defaultBrakeParams();

cfg.projectRoot = string(projectRoot);
cfg.modelName = "carsim_brake_cosim";
cfg.modelPath = fullfile(projectRoot, "models", cfg.modelName + ".slx");
cfg.seedModelPath = fullfile(projectRoot, "models", "carsim_seed_model.slx");
cfg.carSimBlockPath = cfg.modelName + "/CarSimVehicle";

cfg.importVariables = ["IMP_PBK_L1", "IMP_PBK_L2", ...
    "IMP_PBK_R1", "IMP_PBK_R2"];
cfg.exportVariables = ["Vx_SM", "Ax_SM"];
cfg.speedExportIndex = 1;
cfg.accelExportIndex = 2;

% These defaults match common CarSim user units. Change them if the Run
% export table is configured directly in SI units.
cfg.pressureToCarSim = 1.0; % project MPa -> CarSim brake-pressure user unit
cfg.speedToMps = 1 / 3.6;   % CarSim km/h -> m/s
cfg.accelToMps2 = p.g;      % CarSim g -> m/s^2

cfg.massKg = p.m;
cfg.gravityMps2 = p.g;
cfg.referenceBrakeGainNPerMPa = p.kBrake;
cfg.pressureMinMPa = 0;
cfg.pressureMaxMPa = 10;
cfg.datasetStepS = p.dt;
cfg.carSimStepS = 0.001;
cfg.defaultStopTimeS = 6.0;
cfg.initialSpeedToleranceKph = 5.0;

% Set this after running inspect_carsim_interface if a manifest supplies a
% different CarSim .sim/run file for each condition. Examples vary across
% CarSim versions, so it is intentionally not guessed.
cfg.runFileDialogParameter = "";
end


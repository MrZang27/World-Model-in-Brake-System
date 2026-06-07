function result = calibrate_carsim_brake_gain(datasetOrCsv, options)
%CALIBRATE_CARSIM_BRAKE_GAIN Estimate CarSim's low-slip brake-force gain.
%
% This compares CarSim behavior with the current mechanism-model reference
% kBrake = 3500 N/MPa. Use dry-road, non-saturated samples for calibration.

arguments
    datasetOrCsv
    options.MinSpeedMps (1,1) double = 5
    options.MaxPressureMPa (1,1) double = 3
    options.MinMu (1,1) double = 0.6
end

if istable(datasetOrCsv)
    data = datasetOrCsv;
else
    data = readtable(datasetOrCsv);
end
p = defaultBrakeParams();

mask = data.v_mps >= options.MinSpeedMps & ...
    data.pressure_MPa > 0.1 & ...
    data.pressure_MPa <= options.MaxPressureMPa & ...
    data.mu >= options.MinMu & ...
    data.a_next_mps2 < -0.05;

if nnz(mask) < 20
    error("CarSim:CalibrationSamples", ...
        "Not enough low-slip samples for brake-gain calibration.");
end

pressure = data.pressure_MPa(mask);
force = -p.m * data.a_next_mps2(mask);
kEstimated = pressure \ force;
forcePred = pressure * kEstimated;
r2 = 1 - sum((force - forcePred).^2) / ...
    sum((force - mean(force)).^2);

result = struct();
result.kBrakeEstimatedNPerMPa = kEstimated;
result.kBrakeReferenceNPerMPa = p.kBrake;
result.relativeDifference = (kEstimated - p.kBrake) / p.kBrake;
result.r2 = r2;
result.sampleCount = nnz(mask);

fprintf("Estimated CarSim brake gain: %.1f N/MPa\n", kEstimated);
fprintf("Mechanism reference gain:     %.1f N/MPa\n", p.kBrake);
fprintf("Relative difference:          %.1f %%\n", ...
    100 * result.relativeDifference);
fprintf("Calibration R2:               %.4f\n", r2);
end


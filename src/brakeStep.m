function [nextState, info] = brakeStep(state, pressureMPa, mu, p)
%BRAKESTEP One-step simplified longitudinal brake dynamics.
% state = [v, a], where v is m/s and a is m/s^2.

if nargin < 4
    p = defaultBrakeParams();
end

v = max(state(1), p.minSpeed);
pressureMPa = max(pressureMPa, 0);
mu = max(mu, 0.01);

fBrake = p.kBrake * pressureMPa;
fMax = mu * p.m * p.g;
fActual = min(fBrake, fMax);

a = -fActual / p.m;
vNext = max(v + a * p.dt, p.minSpeed);

nextState = [vNext, a];
info = struct();
info.fBrake = fBrake;
info.fMax = fMax;
info.fActual = fActual;
info.utilization = fBrake / max(fMax, eps); %% Avoid division by zero.
info.slipRisk = info.utilization > p.slipPressureRatio;
end

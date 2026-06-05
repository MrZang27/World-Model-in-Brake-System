function p = defaultBrakeParams()
%DEFAULTBRAKEPARAMS Parameters for the simplified braking mechanism model.

p.m = 1800;              % vehicle mass, kg
p.g = 9.81;              % gravity, m/s^2
p.kBrake = 3500;         % brake force per MPa, N/MPa
p.dt = 0.05;             % simulation step, s
p.minSpeed = 0;          % speed lower bound, m/s
p.slipPressureRatio = 0.95;
p.maxComfortDecel = 8.0; % m/s^2, planning envelope
end

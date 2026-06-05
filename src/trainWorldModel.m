function [model, history] = trainWorldModel(X, Y, options)
%TRAINWORLDMODEL Train a small pure-MATLAB MLP world model.

arguments
    X double
    Y double
    options.HiddenSize (1,1) double = 32
    options.Epochs (1,1) double = 250
    options.BatchSize (1,1) double = 256
    options.LearnRate (1,1) double = 0.005
    options.ValidationFraction (1,1) double = 0.2
end

rng(11);
n = size(X, 1);
idx = randperm(n);
nVal = max(1, round(options.ValidationFraction * n));
valIdx = idx(1:nVal);
trainIdx = idx(nVal + 1:end);

xMu = mean(X(trainIdx, :), 1);
xSig = std(X(trainIdx, :), 0, 1) + eps;
yMu = mean(Y(trainIdx, :), 1);
ySig = std(Y(trainIdx, :), 0, 1) + eps;

Xn = (X - xMu) ./ xSig;
Yn = (Y - yMu) ./ ySig;

dIn = size(X, 2);
dH = options.HiddenSize;
dOut = size(Y, 2);

params.W1 = 0.1 * randn(dIn, dH);
params.b1 = zeros(1, dH);
params.W2 = 0.1 * randn(dH, dH);
params.b2 = zeros(1, dH);
params.W3 = 0.1 * randn(dH, dOut);
params.b3 = zeros(1, dOut);

adam = initAdam(params);
history.trainLoss = zeros(options.Epochs, 1);
history.valLoss = zeros(options.Epochs, 1);

for epoch = 1:options.Epochs
    order = trainIdx(randperm(numel(trainIdx)));
    for s = 1:options.BatchSize:numel(order)
        batch = order(s:min(s + options.BatchSize - 1, numel(order)));
        [~, grads] = mlpLoss(params, Xn(batch, :), Yn(batch, :));
        [params, adam] = adamStep(params, grads, adam, options.LearnRate);
    end

    history.trainLoss(epoch) = mlpLoss(params, Xn(trainIdx, :), Yn(trainIdx, :));
    history.valLoss(epoch) = mlpLoss(params, Xn(valIdx, :), Yn(valIdx, :));
end

model = struct();
model.params = params;
model.xMu = xMu;
model.xSig = xSig;
model.yMu = yMu;
model.ySig = ySig;
model.inputNames = {'v_mps', 'a_mps2', 'pressure_MPa', 'mu'};
model.outputNames = {'v_next_mps', 'a_next_mps2'};
model.options = options;
model.validationIndex = valIdx;
model.trainIndex = trainIdx;

fprintf('World model trained. Final validation MSE: %.6f\n', history.valLoss(end));
end

function [loss, grads] = mlpLoss(params, X, Y)
[YHat, cache] = mlpForward(params, X);
err = YHat - Y;
loss = mean(err(:).^2);

if nargout < 2
    return;
end

dY = 2 * err / numel(err);

grads.W3 = cache.h2' * dY;
grads.b3 = sum(dY, 1);

dH2 = dY * params.W3';
dZ2 = dH2 .* (cache.z2 > 0);
grads.W2 = cache.h1' * dZ2;
grads.b2 = sum(dZ2, 1);

dH1 = dZ2 * params.W2';
dZ1 = dH1 .* (cache.z1 > 0);
grads.W1 = X' * dZ1;
grads.b1 = sum(dZ1, 1);
end

function [YHat, cache] = mlpForward(params, X)
cache.z1 = X * params.W1 + params.b1;
cache.h1 = max(cache.z1, 0);
cache.z2 = cache.h1 * params.W2 + params.b2;
cache.h2 = max(cache.z2, 0);
YHat = cache.h2 * params.W3 + params.b3;
end

function adam = initAdam(params)
names = fieldnames(params);
adam.t = 0;
for i = 1:numel(names)
    adam.m.(names{i}) = zeros(size(params.(names{i})));
    adam.v.(names{i}) = zeros(size(params.(names{i})));
end
end

function [params, adam] = adamStep(params, grads, adam, lr)
beta1 = 0.9;
beta2 = 0.999;
epsAdam = 1e-8;
adam.t = adam.t + 1;
names = fieldnames(params);
for i = 1:numel(names)
    name = names{i};
    adam.m.(name) = beta1 * adam.m.(name) + (1 - beta1) * grads.(name);
    adam.v.(name) = beta2 * adam.v.(name) + (1 - beta2) * grads.(name).^2;
    mHat = adam.m.(name) / (1 - beta1^adam.t);
    vHat = adam.v.(name) / (1 - beta2^adam.t);
    params.(name) = params.(name) - lr * mHat ./ (sqrt(vHat) + epsAdam);
end
end

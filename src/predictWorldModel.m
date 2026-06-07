function YHat = predictWorldModel(model, X)
%PREDICTWORLDMODEL Predict next braking state with the trained MLP.

Xn = (X - model.xMu) ./ model.xSig; % Normalize inputs.
params = model.params; % Extract parameters for cleaner code.
z1 = Xn * params.W1 + params.b1; % Linear layer before ReLU.
h1 = max(z1, 0); % ReLU activation.
z2 = h1 * params.W2 + params.b2; % Linear layer before ReLU.
h2 = max(z2, 0); % ReLU activation.
Yn = h2 * params.W3 + params.b3; % Linear output layer.
YHat = Yn .* model.ySig + model.yMu; % Rescale to original units.
YHat(:, 1) = max(YHat(:, 1), 0); % Speed cannot be negative.
end

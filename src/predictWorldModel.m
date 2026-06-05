function YHat = predictWorldModel(model, X)
%PREDICTWORLDMODEL Predict next braking state with the trained MLP.

Xn = (X - model.xMu) ./ model.xSig;
params = model.params;
z1 = Xn * params.W1 + params.b1;
h1 = max(z1, 0);
z2 = h1 * params.W2 + params.b2;
h2 = max(z2, 0);
Yn = h2 * params.W3 + params.b3;
YHat = Yn .* model.ySig + model.yMu;
YHat(:, 1) = max(YHat(:, 1), 0);
end

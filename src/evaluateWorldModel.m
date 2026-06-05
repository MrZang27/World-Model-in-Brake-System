function metrics = evaluateWorldModel(model, X, Y)
%EVALUATEWORLDMODEL Compute MSE, MAE, and R2 for the world model.

YHat = predictWorldModel(model, X);
err = YHat - Y;
metrics.mse = mean(err.^2, 1);
metrics.mae = mean(abs(err), 1);
ssRes = sum(err.^2, 1);
ssTot = sum((Y - mean(Y, 1)).^2, 1);
metrics.r2 = 1 - ssRes ./ ssTot;
metrics.prediction = YHat;
end

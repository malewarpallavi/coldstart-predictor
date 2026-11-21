"""Train the gradient-boosting model and export it as JSON for the predictor Lambda."""
import json, os, runpy
import numpy as np

ns = runpy.run_path("notebooks/forecast_experiment.py")   # reuse data + trained model
gbr, feats, test = ns["gbr"], ns["feats"], ns["test"]

model = {
    "features": feats,
    "init": float(gbr.init_.constant_[0][0]),
    "lr": float(gbr.learning_rate),
    "trees": [
        {"left": t.tree_.children_left.tolist(), "right": t.tree_.children_right.tolist(),
         "feature": t.tree_.feature.tolist(),
         "threshold": [round(x, 6) for x in t.tree_.threshold.tolist()],
         "value": [round(float(v), 6) for v in t.tree_.value[:, 0, 0]]}
        for t in gbr.estimators_[:, 0]
    ],
}
os.makedirs("predictor", exist_ok=True)
json.dump(model, open("predictor/model.json", "w"))

def predict(m, row):                                  # pure python, no sklearn
    total = m["init"]
    for t in m["trees"]:
        i = 0
        while t["left"][i] != -1:
            i = t["left"][i] if row[t["feature"][i]] <= t["threshold"][i] else t["right"][i]
        total += m["lr"] * t["value"][i]
    return total

X = test[feats].values[:300]
mine = np.array([predict(model, r) for r in X])
print("max diff vs sklearn:", float(np.abs(mine - gbr.predict(test[feats].iloc[:300])).max()))
print("model.json size KB:", round(os.path.getsize("predictor/model.json") / 1024))

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
print("model.json size KB:", round(os.path.getsize("predictor/model.json") / 1024))

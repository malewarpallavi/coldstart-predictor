"""Compare a smoothing baseline against gradient boosting on simulated traffic.

Task: given traffic up to minute t, predict requests in minute t+H (H = pre-warm lead time).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

rng = np.random.default_rng(42)
H = 2          # forecast horizon in minutes (pre-warm lead time)
SPIKE = 20     # requests/min above which we call it a spike
DAYS = 14

# ---------- 1. simulate per-minute traffic ----------
n = DAYS * 24 * 60
t = np.arange(n)
mod = t % 1440
traffic = 4 + 3 * np.sin(2 * np.pi * (mod - 540) / 1440)         # daily cycle
for k in range(n):                                                # scheduled spikes: top of each hour
    if t[k] % 60 in (0, 1, 2) and 480 <= mod[k] <= 1200:
        traffic[k] += 35
for _ in range(DAYS * 6):                                         # random, unpredictable bursts
    s = rng.integers(0, n - 6)
    traffic[s:s + rng.integers(2, 6)] += rng.integers(20, 40)
y = rng.poisson(np.clip(traffic, 0, None)).astype(float)

# ---------- 2. features ----------
df = pd.DataFrame({"y": y})
for lag in (1, 2, 3, 5, 10, 15):
    df[f"lag{lag}"] = df["y"].shift(lag - 1)                      # lag1 = current minute
df["roll5"] = df["y"].rolling(5).mean()
df["diff1"] = df["y"] - df["y"].shift(1)
df["min_of_hour"] = t % 60
df["tod_sin"] = np.sin(2 * np.pi * mod / 1440)
df["tod_cos"] = np.cos(2 * np.pi * mod / 1440)
df["target"] = df["y"].shift(-H)
df = df.dropna()
split = int(len(df) * 0.75)                                       # time-ordered split, no shuffling
feats = [c for c in df.columns if c not in ("y", "target")]
train, test = df.iloc[:split], df.iloc[split:]

# ---------- 3. models ----------
def ses(series, alpha=0.5):
    out, level = [], series[0]
    for v in series:
        level = alpha * v + (1 - alpha) * level
        out.append(level)
    return np.array(out)

ses_pred = pd.Series(ses(df["y"].values), index=df.index).loc[test.index]
gbr = GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                learning_rate=0.05, random_state=0)
gbr.fit(train[feats], train["target"])
gbr_pred = gbr.predict(test[feats])

# ---------- 4. evaluate ----------
actual = test["target"].values

def report(name, pred):
    pred = np.asarray(pred)
    is_spike, flagged = actual > SPIKE, pred > SPIKE * 0.6        # flag early at 60% of spike level
    tp = (is_spike & flagged).sum()
    print(f"{name:22s} MAE={mean_absolute_error(actual, pred):5.2f}  "
          f"spike recall={tp / max(is_spike.sum(), 1):4.0%}  "
          f"precision={tp / max(flagged.sum(), 1):4.0%}")

print(f"test minutes={len(test)}, spike minutes={(actual > SPIKE).sum()}")
report("smoothing (baseline)", ses_pred.values)
report("gradient boosting", gbr_pred)
imp = pd.Series(gbr.feature_importances_, index=feats).sort_values(ascending=False)
print("\ntop features:\n", imp.head(5).round(3).to_string())

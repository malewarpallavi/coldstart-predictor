"""Compare a smoothing baseline against gradient boosting on simulated traffic.

Workload: light background traffic plus a spike every PERIOD minutes
(compressed from real-world schedules so the live benchmark fits in hours).
Task: given traffic up to minute t, predict requests in minute t+H.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

rng = np.random.default_rng(42)
H = 2            # forecast horizon in minutes (pre-warm lead time)
SPIKE = 20       # requests/min above which we call it a spike
PERIOD = 5       # a scheduled spike every PERIOD minutes
SPIKE_ADD = 25   # extra requests/min during a scheduled spike
DAYS = 14

# ---------- 1. simulate per-minute traffic ----------
n = DAYS * 24 * 60
t = np.arange(n)
traffic = 3.5 + 1.0 * np.sin(2 * np.pi * (t % 1440) / 1440)       # light background
active = np.zeros(n, dtype=bool)                                   # the schedule switches on/off in blocks,
pos, on = 0, True                                                  # so the model must check recent traffic
while pos < n:
    length = int(rng.integers(40, 150))
    active[pos:pos + length] = on
    pos, on = pos + length, not on
traffic[(t % PERIOD == 0) & active] += SPIKE_ADD                   # scheduled spikes (only while active)
for _ in range(DAYS * 3):                                          # random, unpredictable bursts
    s = rng.integers(0, n - 6)
    traffic[s:s + rng.integers(2, 5)] += rng.integers(15, 30)
y = rng.poisson(np.clip(traffic, 0, None)).astype(float)

# ---------- 2. features (the predictor Lambda recomputes exactly these) ----------
df = pd.DataFrame({"y": y})
for lag in (1, 2, 3, 5, 10, 15):
    df[f"lag{lag}"] = df["y"].shift(lag - 1)                       # lag1 = current minute
df["roll5"] = df["y"].rolling(5).mean()
df["max15"] = df["y"].rolling(15).max()                            # was there a spike recently?
df["diff1"] = df["y"] - df["y"].shift(1)
df["min_of_period"] = t % PERIOD
df["target"] = df["y"].shift(-H)
df = df.dropna()
split = int(len(df) * 0.75)                                        # time-ordered split, no shuffling
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
gbr = GradientBoostingRegressor(n_estimators=150, max_depth=3,
                                learning_rate=0.05, random_state=0)
gbr.fit(train[feats], train["target"])
gbr_pred = gbr.predict(test[feats])

# ---------- 4. evaluate ----------
actual = test["target"].values

def report(name, pred):
    pred = np.asarray(pred)
    is_spike, flagged = actual > SPIKE, pred > SPIKE * 0.6         # flag early at 60% of spike level
    tp = (is_spike & flagged).sum()
    print(f"{name:22s} MAE={mean_absolute_error(actual, pred):5.2f}  "
          f"spike recall={tp / max(is_spike.sum(), 1):4.0%}  "
          f"precision={tp / max(flagged.sum(), 1):4.0%}")

if __name__ == "__main__":
    print(f"test minutes={len(test)}, spike minutes={(actual > SPIKE).sum()}")
    report("smoothing (baseline)", ses_pred.values)
    report("gradient boosting", gbr_pred)
    imp = pd.Series(gbr.feature_importances_, index=feats).sort_values(ascending=False)
    print("\ntop features:\n", imp.head(5).round(3).to_string())

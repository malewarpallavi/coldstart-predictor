"""Predictor Lambda: runs every minute (EventBridge), forecasts load 2 minutes ahead,
and pre-warms containers of the target function when a spike is expected."""
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3.dynamodb.conditions import Key

TABLE = os.environ["TABLE_NAME"]
TARGET_FN = os.environ["TARGET_FN"]            # also the DynamoDB partition key
ALIAS = os.environ.get("ALIAS", "live")
WARM_THRESHOLD = float(os.environ.get("WARM_THRESHOLD", "12"))   # forecast req/min that triggers warming
PER_CONTAINER = float(os.environ.get("PER_CONTAINER", "6"))      # req/min one warm container "covers"
MAX_WARM = int(os.environ.get("MAX_WARM", "5"))                  # stay well under the account limit
HOLD_MS = int(os.environ.get("HOLD_MS", "1500"))                 # keep each ping in flight so pings land on distinct containers

_table = boto3.resource("dynamodb").Table(TABLE)
_lam = boto3.client("lambda")
with open(os.path.join(os.path.dirname(__file__), "model.json")) as f:
    MODEL = json.load(f)


# ---------- forecasting ----------
def history(m, n=15):
    """Request counts for minutes m-n+1 .. m (oldest first); m = last complete minute."""
    resp = _table.query(KeyConditionExpression=Key("fn").eq(TARGET_FN) &
                        Key("ts_min").between(m - n + 1, m))
    got = {int(i["ts_min"]): float(i["total"]) for i in resp["Items"]}
    return [got.get(k, 0.0) for k in range(m - n + 1, m + 1)]


def features(counts, m):
    """Must match the training features in notebooks/forecast_experiment.py."""
    f = {f"lag{k}": counts[-k] for k in (1, 2, 3, 5, 10, 15)}
    f["roll5"] = sum(counts[-5:]) / 5
    f["diff1"] = counts[-1] - counts[-2]
    f["min_of_period"] = m % 5
    return [f[name] for name in MODEL["features"]]


def predict(row):
    total = MODEL["init"]
    for t in MODEL["trees"]:
        i = 0
        while t["left"][i] != -1:
            i = t["left"][i] if row[t["feature"][i]] <= t["threshold"][i] else t["right"][i]
        total += MODEL["lr"] * t["value"][i]
    return total


# ---------- config + warming ----------
def get_config():
    item = _table.get_item(Key={"fn": "config", "ts_min": 0}).get("Item", {})
    return {"strategy": item.get("strategy", "predictive"),
            "fixed_n": int(item.get("fixed_n", 5)),
            "fixed_every": int(item.get("fixed_every", 3))}


def _ping(_):
    r = _lam.invoke(FunctionName=TARGET_FN, Qualifier=ALIAS,
                    Payload=json.dumps({"warm": True, "hold_ms": HOLD_MS}))
    return json.loads(r["Payload"].read())


def warm(n, m):
    if n <= 0:
        return 0
    with ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(_ping, range(n)))
    new = sum(1 for r in results if r.get("cold"))
    # cost accounting: how many warm pings, and how many created a new container
    _table.update_item(Key={"fn": "warmlog", "ts_min": m},
                       UpdateExpression="SET #e = :exp ADD pings :n, new_containers :c",
                       ExpressionAttributeNames={"#e": "expires"},
                       ExpressionAttributeValues={":exp": int(time.time()) + 7 * 86400,
                                                  ":n": n, ":c": new})
    return new


def handler(event, context):
    now_min = int(time.time()) // 60
    m = now_min - 1                      # last complete minute
    cfg = get_config()
    out = {"strategy": cfg["strategy"], "minute": m, "forecast": None, "warm": 0, "new_containers": 0}

    if cfg["strategy"] == "predictive":
        counts = history(m)
        forecast = predict(features(counts, m))
        out["forecast"] = round(forecast, 2)
        if forecast >= WARM_THRESHOLD:
            out["warm"] = max(1, min(MAX_WARM, math.ceil(forecast / PER_CONTAINER)))
    elif cfg["strategy"] == "fixed" and now_min % cfg["fixed_every"] == 0:
        out["warm"] = min(MAX_WARM, cfg["fixed_n"])
    # strategy "off": do nothing

    out["new_containers"] = warm(out["warm"], m)
    print(json.dumps({"type": "decision", **out}))
    return out

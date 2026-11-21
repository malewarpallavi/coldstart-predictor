import json
import os
import time
import uuid

import boto3

# --- runs ONCE per container (this is the cold-start phase) ---
time.sleep(int(os.environ.get("INIT_DELAY_MS", "0")) / 1000)  # simulate heavy init
_table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
_container_id = str(uuid.uuid4())
_is_cold = True
TTL_SECONDS = 7 * 24 * 3600


def handler(event, context):
    global _is_cold
    start = time.perf_counter()
    cold, _is_cold = _is_cold, False

    # Warm-up ping from the predictor: hold the container busy so parallel pings
    # land on distinct containers, and do NOT count it as user traffic.
    if isinstance(event, dict) and event.get("warm"):
        time.sleep(int(event.get("hold_ms", 1500)) / 1000)
        return {"warmed": True, "cold": cold, "container": _container_id}

    # simulated work
    work_ms = int((event.get("queryStringParameters") or {}).get("ms", 20))
    end = start + work_ms / 1000
    while time.perf_counter() < end:
        pass

    # per-minute counters: one atomic increment, no read-modify-write
    now = int(time.time())
    _table.update_item(
        Key={"fn": context.function_name, "ts_min": now // 60},
        UpdateExpression="SET #e = :exp ADD #t :one, #c :cold",
        ExpressionAttributeNames={"#e": "expires", "#t": "total", "#c": "cold"},
        ExpressionAttributeValues={
            ":exp": now + TTL_SECONDS,
            ":one": 1,
            ":cold": 1 if cold else 0,
        },
    )

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    print(json.dumps({"type": "invocation", "cold": cold, "latency_ms": latency_ms,
                      "container": _container_id}))
    return {
        "statusCode": 200,
        "body": json.dumps({"cold": cold, "latency_ms": latency_ms,
                            "container": _container_id}),
    }

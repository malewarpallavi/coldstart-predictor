"""Benchmark one warming strategy (off | fixed | predictive) against the live stack.

Every 5 minutes (aligned to the clock) a spike arrives: 7 waves of 4 concurrent requests.
Between spikes there is light background traffic. After each spike the function's containers
are rotated (new version) so the next spike starts cold unless a strategy warms it.

Usage:  python loadtest/benchmark.py --strategy predictive
"""
import argparse, csv, json, os, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3.dynamodb.conditions import Key

CYCLE = 300                      # seconds between spikes (matches the model's training schedule)
WAVES, WAVE_SIZE = 7, 4          # spike = 28 requests, at most 4 in flight at once
BG_AT = [90, 100, 110, 135, 145, 155, 195, 205, 215, 255, 265, 275]   # 3 background req/min
HOLD_S, INIT_S, MEM_GB, PRICE_GB_S = 1.5, 0.8, 0.25, 0.0000166667      # cost model (approximate)


def sleep_until(ts):
    d = ts - time.time()
    if d > 0:
        time.sleep(d)


def p95(vals):
    v = sorted(vals)
    return round(v[int(round(0.95 * (len(v) - 1)))], 1) if v else None


def call(url, kind, cycle, results, lock):
    t0, status, body = time.perf_counter(), 0, {}
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            status, body = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:
        status = 0
    ms = (time.perf_counter() - t0) * 1000
    with lock:
        results.append({"cycle": cycle, "kind": kind, "ts": round(time.time(), 2), "status": status,
                        "cold": body.get("cold"), "client_ms": round(ms, 1),
                        "server_ms": body.get("latency_ms"), "container": str(body.get("container", ""))[:8]})


def make_clients(region):
    return (boto3.client("lambda", region_name=region), boto3.resource("dynamodb", region_name=region),
            boto3.client("cloudformation", region_name=region))


def rotate(lam, fn):
    """Publish a new version and point the 'live' alias at it: all containers start cold."""
    cfg = lam.get_function_configuration(FunctionName=fn)
    env = dict(cfg.get("Environment", {}).get("Variables", {}))
    env["ROTATE"] = str(time.time())
    lam.update_function_configuration(FunctionName=fn, Environment={"Variables": env})
    lam.get_waiter("function_updated_v2").wait(FunctionName=fn)
    ver = lam.publish_version(FunctionName=fn)["Version"]
    lam.update_alias(FunctionName=fn, Name="live", FunctionVersion=ver)


def set_strategy(table, strategy):
    table.put_item(Item={"fn": "config", "ts_min": 0, "strategy": strategy,
                         "fixed_n": 4, "fixed_every": 3})


def cycle_stats(results, c):
    sp = [r for r in results if r["kind"] == "spike" and r["cycle"] == c]
    ok = [r["client_ms"] for r in sp if r["status"] == 200]
    return {"n": len(sp), "errors": len(sp) - len(ok), "cold": sum(1 for r in sp if r["cold"] is True),
            "p95": p95(ok)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["off", "fixed", "predictive"], required=True)
    ap.add_argument("--cycles", type=int, default=6, help="measured cycles")
    ap.add_argument("--warmup", type=int, default=1, help="unmeasured cycles first")
    ap.add_argument("--scale", type=float, default=1.0, help="time scale (tests only)")
    ap.add_argument("--region", default="ap-south-1")
    ap.add_argument("--stack", default="coldstart-predictor")
    ap.add_argument("--url", default=None)
    a = ap.parse_args()

    lam, ddb, cfn = make_clients(a.region)
    outs = {o["OutputKey"]: o["OutputValue"] for o in
            cfn.describe_stacks(StackName=a.stack)["Stacks"][0]["Outputs"]}
    url, fn, table = a.url or outs["FunctionUrl"], outs["TargetFunctionName"], ddb.Table(outs["TableName"])
    sc, cyc = a.scale, CYCLE * a.scale

    print(f"[{a.strategy}] setting strategy and rotating containers ...", flush=True)
    set_strategy(table, a.strategy)
    rotate(lam, fn)
    S = (int(time.time() // cyc) + 1) * cyc
    if S - time.time() < 90 * sc:
        S += cyc
    total = a.warmup + a.cycles
    print(f"[{a.strategy}] {total} cycles ({a.warmup} warm-up), first spike in {S - time.time():.0f}s", flush=True)

    results, lock = [], threading.Lock()
    with ThreadPoolExecutor(max_workers=64) as pool:
        for i in range(total):
            s = S + i * cyc
            if i > 0:
                st = cycle_stats(results, i - 1)
                tag = "warm-up" if i - 1 < a.warmup else "measured"
                print(f"  cycle {i - 1} ({tag}): spike n={st['n']} cold={st['cold']} "
                      f"errors={st['errors']} p95={st['p95']}ms", flush=True)
            for w in range(WAVES):                       # spike
                sleep_until(s + (8 + w * 6.5) * sc)
                for _ in range(WAVE_SIZE):
                    pool.submit(call, url, "spike", i, results, lock)
            if i < total - 1:                            # reset containers for the next spike
                sleep_until(s + 62 * sc)
                rotate(lam, fn)
                for off in BG_AT:                        # light background traffic
                    sleep_until(s + off * sc)
                    pool.submit(call, url, "bg", i, results, lock)
        sleep_until(S + (total - 1) * cyc + 30 * sc)
    st = cycle_stats(results, total - 1)
    print(f"  cycle {total - 1} (measured): spike n={st['n']} cold={st['cold']} "
          f"errors={st['errors']} p95={st['p95']}ms", flush=True)

    set_strategy(table, "off")                           # stop any warming
    meas = [r for r in results if r["kind"] == "spike" and r["cycle"] >= a.warmup]
    ok = [r["client_ms"] for r in meas if r["status"] == 200]
    t0 = int((S + a.warmup * cyc) // 60) - 2
    t1 = int(time.time() // 60)
    pings = new = 0
    for it in table.query(KeyConditionExpression=Key("fn").eq("warmlog") &
                          Key("ts_min").between(t0, t1))["Items"]:
        pings += int(it.get("pings", 0)); new += int(it.get("new_containers", 0))
    summary = {
        "strategy": a.strategy, "measured_cycles": a.cycles, "spike_requests": len(meas),
        "errors": len(meas) - len(ok), "cold_starts": sum(1 for r in meas if r["cold"] is True),
        "cold_rate_pct": round(100 * sum(1 for r in meas if r["cold"] is True) / max(len(meas), 1), 1),
        "avg_ms": round(sum(ok) / len(ok), 1) if ok else None, "p95_ms": p95(ok),
        "warm_pings": pings, "new_containers_from_pings": new,
        "warm_cost_usd": round((pings * HOLD_S + new * INIT_S) * MEM_GB * PRICE_GB_S, 6),
    }
    os.makedirs("loadtest", exist_ok=True)
    with open(f"loadtest/bench_{a.strategy}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys())); w.writeheader()
        w.writerows(sorted(results, key=lambda r: r["ts"]))
    json.dump(summary, open(f"loadtest/summary_{a.strategy}.json", "w"), indent=2)
    print("\nSUMMARY", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

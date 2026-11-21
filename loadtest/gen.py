import argparse, csv, json, math, os, random, threading, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def rps_at(p, t, a):
    if p == "steady":
        return a.rps
    if p == "burst":  # low base traffic with a periodic spike
        return a.peak if (t % a.period) < a.burst_len else a.rps
    if p == "cycle":  # smooth wave between rps and peak
        mid, amp = (a.peak + a.rps) / 2, (a.peak - a.rps) / 2
        return mid + amp * math.sin(2 * math.pi * t / a.period)
    raise ValueError(p)


def call(url, rows, lock):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            body, status = json.loads(r.read()), 200
    except Exception as e:
        body, status = {}, getattr(e, "code", 0)
    ms = (time.perf_counter() - start) * 1000
    with lock:
        rows.append([int(time.time()), status, body.get("cold"),
                     round(ms, 1), str(body.get("container", ""))[:8]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", choices=["steady", "burst", "cycle"], default="steady")
    ap.add_argument("--duration", type=int, default=60, help="seconds")
    ap.add_argument("--rps", type=float, default=1, help="base requests/sec")
    ap.add_argument("--peak", type=float, default=4, help="peak requests/sec")
    ap.add_argument("--period", type=int, default=30, help="seconds per cycle")
    ap.add_argument("--burst-len", type=int, default=5, help="seconds per burst")
    ap.add_argument("--out", default="loadtest/run.csv")
    a = ap.parse_args()

    url, rows, lock = os.environ["URL"], [], threading.Lock()
    with ThreadPoolExecutor(max_workers=32) as pool:
        for t in range(a.duration):
            tick = time.perf_counter()
            r = rps_at(a.pattern, t, a)
            n = int(r) + (random.random() < r - int(r))
            for _ in range(n):
                pool.submit(call, url, rows, lock)
                time.sleep(1 / n)
            time.sleep(max(0, 1 - (time.perf_counter() - tick)))

    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "status", "cold", "latency_ms", "container"])
        w.writerows(sorted(rows))

    ok = sorted(r[3] for r in rows if r[1] == 200)
    cold = sum(1 for r in rows if r[2] is True)
    errors = len(rows) - len(ok)
    if ok:
        print(f"requests={len(rows)} ok={len(ok)} errors={errors} cold={cold} "
              f"p50={ok[len(ok) // 2]}ms p95={ok[int(len(ok) * 0.95)]}ms")
    else:
        print("no successful requests, check URL / throttling")


main()
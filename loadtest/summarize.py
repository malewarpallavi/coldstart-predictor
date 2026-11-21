"""Merge the three benchmark runs into one table (markdown) and one chart (PNG)."""
import collections, csv, json, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["off", "fixed", "predictive"]
rows = []
for s in ORDER:
    sm = json.load(open(f"loadtest/summary_{s}.json"))
    allrows = list(csv.DictReader(open(f"loadtest/bench_{s}.csv")))
    warmup = (max(int(r["cycle"]) for r in allrows) + 1) - sm["measured_cycles"]
    spikes = [r for r in allrows if r["kind"] == "spike" and int(r["cycle"]) >= warmup]
    ok = [float(r["client_ms"]) for r in spikes if r["status"] == "200"]
    errs = collections.Counter(r["status"] for r in spikes if r["status"] != "200")
    cold = [float(r["client_ms"]) for r in spikes if r["status"] == "200" and r["cold"] == "True"]
    warm = [float(r["client_ms"]) for r in spikes if r["status"] == "200" and r["cold"] == "False"]
    rows.append({"s": s, "n": len(spikes), "cold": sm["cold_starts"], "rate": sm["cold_rate_pct"],
                 "median": round(statistics.median(ok)) if ok else None, "p95": round(sm["p95_ms"]),
                 "errors": dict(errs) or "-", "pings": sm["warm_pings"], "cost": sm["warm_cost_usd"],
                 "penalty": round(statistics.mean(cold) - statistics.median(warm)) if cold and warm else None})

print("| Strategy | Spike req | Cold starts | Cold rate | Median ms | p95 ms | Errors | Warm pings | Ping cost (USD) |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r['s']} | {r['n']} | {r['cold']} | {r['rate']}% | {r['median']} | {r['p95']} | "
          f"{r['errors']} | {r['pings']} | {r['cost']:.6f} |")
for r in rows:
    if r["penalty"] is not None:
        print(f"\n{r['s']}: a cold request took about {r['penalty']} ms longer than a warm one "
              f"(client-side, includes network noise)")

fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
names = [r["s"] for r in rows]
colors = ["#c0504d", "#4f81bd", "#2e8b57"]
ax[0].bar(names, [r["rate"] for r in rows], color=colors); ax[0].set_title("Cold-start rate (%)")
x = range(len(rows))
ax[1].bar([i - 0.2 for i in x], [r["median"] for r in rows], 0.4, label="median", color="#9bbb59")
ax[1].bar([i + 0.2 for i in x], [r["p95"] for r in rows], 0.4, label="p95", color="#8064a2")
ax[1].set_xticks(list(x)); ax[1].set_xticklabels(names); ax[1].set_title("Client latency (ms)"); ax[1].legend()
ax[2].bar(names, [r["cost"] * 1e6 for r in rows], color=colors); ax[2].set_title("Warm-ping cost (micro-USD)")
for a in ax:
    a.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("loadtest/results.png", dpi=150)
print("\nsaved loadtest/results.png")

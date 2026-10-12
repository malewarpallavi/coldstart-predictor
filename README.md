# ColdStart Predictor

Predictive pre-warming for Google Cloud Run: lower cold-start latency without paying for always-on instances.

## Problem

Serverless platforms like Cloud Run start a new container when traffic spikes or arrives after idle time. That first request is slow (a **cold start**), and Java/Spring Boot services are especially affected by JVM startup. The usual fixes are either always keeping instances running (costly) or pinging on a fixed interval (wasteful and blind to real traffic).

This project predicts upcoming traffic from request history and raises Cloud Run `min-instances` only when a spike is expected.

## How it works

```
Client requests
      |
      v
Cloud Run service (Spring Boot)  --logs cold/warm + latency-->  Firestore (invocation history)
      ^                                                                  |
      |                                                                  v
 min-instances update  <--  Predictor (forecasting)  <--  Pub/Sub  <--  Cloud Scheduler (every 1 min)
```

1. The Spring Boot service flags each request as cold or warm and stores its latency.
2. Cloud Scheduler publishes a message to Pub/Sub every minute.
3. The predictor reads recent history and forecasts next-minute traffic (exponential smoothing).
4. If a spike is predicted, it raises Cloud Run `min-instances`; otherwise it scales back down.

## Strategies compared

| Strategy | Description |
|---|---|
| No warming | Default Cloud Run behaviour (min-instances = 0) |
| Fixed-interval | Keep instances warm on a fixed schedule |
| Predictive | Raise min-instances only when forecast predicts a spike |

Each strategy is load tested with k6 (10,000+ requests) and compared on p95 latency, cold-start rate, and cost.

## Tech stack

Java, Spring Boot, Docker, Google Cloud Run, Cloud Scheduler, Pub/Sub, Firestore, Cloud Monitoring, k6

## Build status

- [x] Repository created
- [ ] GCP project and billing budget alert
- [ ] Spring Boot service with cold-start detection
- [ ] Deployed to Cloud Run
- [ ] Invocation history stored in Firestore
- [ ] Forecasting module
- [ ] Cloud Scheduler + Pub/Sub prediction cycle
- [ ] Automatic min-instances updates
- [ ] k6 benchmarks for all 3 strategies
- [ ] Results and analysis

## Results

_To be added after the benchmark._

| Strategy | p95 latency | Cold-start rate | Relative cost |
|---|---|---|---|
| No warming | - | - | - |
| Fixed-interval | - | - | - |
| Predictive | - | - | - |

## Author

Pallavi Malewar

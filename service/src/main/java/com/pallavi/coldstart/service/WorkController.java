package com.pallavi.coldstart.service;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class WorkController {
    private final ColdStartTracker tracker;
    private final InvocationRepository repo;

    public WorkController(ColdStartTracker tracker, InvocationRepository repo) {
        this.tracker = tracker;
        this.repo = repo;
    }

    /** Simulates a small unit of CPU work so latency numbers are not zero. */
    @GetMapping("/work")
    public Map<String, Object> work(@RequestParam(defaultValue = "20") int ms) {
        long start = System.nanoTime();
        boolean cold = tracker.isColdRequest();

        long end = start + ms * 1_000_000L;
        double x = 0;
        while (System.nanoTime() < end) {
            x += Math.sqrt(x + 1);
        }

        long latencyMs = (System.nanoTime() - start) / 1_000_000;
        repo.save(tracker.instanceId(), cold, latencyMs, tracker.jvmUptimeMs());

        return Map.of("cold", cold, "latencyMs", latencyMs, "instanceId", tracker.instanceId());
    }

    @GetMapping("/healthz")
    public String health() {
        return "ok";
    }
}

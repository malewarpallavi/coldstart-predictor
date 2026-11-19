package com.pallavi.coldstart.service;

import java.lang.management.ManagementFactory;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.stereotype.Component;

/**
 * A request is "cold" if it is the first one this container instance ever serves.
 * Cloud Run starts a new container (and so a new JVM) for each new instance,
 * so a fresh static/bean state == a fresh instance.
 */
@Component
public class ColdStartTracker {
    private final AtomicBoolean first = new AtomicBoolean(true);
    private final String instanceId = UUID.randomUUID().toString();

    /** @return true exactly once per instance: for its first request. */
    public boolean isColdRequest() {
        return first.getAndSet(false);
    }

    public String instanceId() {
        return instanceId;
    }

    public long jvmUptimeMs() {
        return ManagementFactory.getRuntimeMXBean().getUptime();
    }
}

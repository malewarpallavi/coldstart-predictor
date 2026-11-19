package com.pallavi.coldstart.service;

import com.google.cloud.firestore.Firestore;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class InvocationRepository {
    private static final Logger log = LoggerFactory.getLogger(InvocationRepository.class);

    private final Optional<Firestore> firestore;
    private final String collection;

    public InvocationRepository(Optional<Firestore> firestore,
                                @Value("${coldstart.collection}") String collection) {
        this.firestore = firestore;
        this.collection = collection;
    }

    /** Fire-and-forget: we never block the request on the history write. */
    public void save(String instanceId, boolean cold, long latencyMs, long jvmUptimeMs) {
        Map<String, Object> doc = new HashMap<>();
        doc.put("ts", System.currentTimeMillis());
        doc.put("instanceId", instanceId);
        doc.put("cold", cold);
        doc.put("latencyMs", latencyMs);
        doc.put("jvmUptimeMs", jvmUptimeMs);
        doc.put("revision", System.getenv().getOrDefault("K_REVISION", "local"));

        if (firestore.isEmpty()) {
            log.info("invocation (firestore disabled): {}", doc);
            return;
        }
        firestore.get().collection(collection).document().set(doc);
    }
}

package com.pallavi.coldstart.service;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.FirestoreOptions;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class FirestoreConfig {
    @Bean
    @ConditionalOnProperty(name = "coldstart.firestore-enabled", havingValue = "true")
    public Firestore firestore() {
        return FirestoreOptions.getDefaultInstance().getService();
    }
}

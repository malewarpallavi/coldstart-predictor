package com.pallavi.coldstart.predictor;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.FirestoreOptions;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class PredictorConfig {
    @Bean
    public Firestore firestore() {
        return FirestoreOptions.getDefaultInstance().getService();
    }

    @Bean
    @ConfigurationProperties(prefix = "predictor")
    public PredictorProperties predictorProperties() {
        return new PredictorProperties();
    }
}

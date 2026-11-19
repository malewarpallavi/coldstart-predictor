package com.pallavi.coldstart.predictor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

/** Pub/Sub push endpoint. Cloud Scheduler -> Pub/Sub -> POST /predict every minute. */
@RestController
public class PredictController {
    private static final Logger log = LoggerFactory.getLogger(PredictController.class);

    private final HistoryReader history;
    private final CloudRunScaler scaler;
    private final PredictorProperties props;

    public PredictController(HistoryReader history, CloudRunScaler scaler, PredictorProperties props) {
        this.history = history;
        this.scaler = scaler;
        this.props = props;
    }

    @PostMapping("/predict")
    public ResponseEntity<Void> predict() {
        try {
            double[] counts = history.perMinuteCounts(System.currentTimeMillis());
            double forecast = Forecaster.forecast(counts, props.getAlpha());
            int target = Forecaster.minInstancesFor(forecast, props.getSpikeThresholdRpm(),
                    props.getRequestsPerInstancePerMinute(), props.getMaxMinInstances());
            log.info("forecast={} rpm -> min-instances={}", String.format("%.2f", forecast), target);
            scaler.setMinInstances(target);
            return ResponseEntity.noContent().build();   // 2xx = ack the Pub/Sub message
        } catch (Exception e) {
            log.error("prediction cycle failed", e);
            return ResponseEntity.status(500).build();   // Pub/Sub will retry
        }
    }
}

package com.pallavi.coldstart.predictor;

import com.google.cloud.run.v2.Service;
import com.google.cloud.run.v2.ServiceName;
import com.google.cloud.run.v2.ServicesClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class CloudRunScaler {
    private static final Logger log = LoggerFactory.getLogger(CloudRunScaler.class);
    private final PredictorProperties props;

    public CloudRunScaler(PredictorProperties props) {
        this.props = props;
    }

    /** Sets min-instances on the target service. No-op if already at the target value. */
    public void setMinInstances(int target) throws Exception {
        if (props.isDryRun()) {
            log.info("[dry-run] would set min-instances={} on {}", target, props.getTargetService());
            return;
        }
        try (ServicesClient client = ServicesClient.create()) {
            ServiceName name = ServiceName.of(props.getGcpProject(), props.getRegion(), props.getTargetService());
            Service svc = client.getService(name);
            int current = svc.getTemplate().getScaling().getMinInstanceCount();
            if (current == target) {
                log.info("min-instances already {}", target);
                return;
            }
            Service updated = svc.toBuilder()
                    .setTemplate(svc.getTemplate().toBuilder()
                            .setScaling(svc.getTemplate().getScaling().toBuilder()
                                    .setMinInstanceCount(target)))
                    .build();
            client.updateServiceAsync(updated).get();
            log.info("min-instances {} -> {}", current, target);
        }
    }
}

package com.pallavi.coldstart.predictor;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import java.util.concurrent.ExecutionException;
import org.springframework.stereotype.Component;

@Component
public class HistoryReader {
    private static final long MINUTE = 60_000L;

    private final Firestore firestore;
    private final PredictorProperties props;

    public HistoryReader(Firestore firestore, PredictorProperties props) {
        this.firestore = firestore;
        this.props = props;
    }

    /** Request counts per minute for the last N complete minutes, oldest first. */
    public double[] perMinuteCounts(long nowMs) throws ExecutionException, InterruptedException {
        int n = props.getWindowMinutes();
        long endBucket = nowMs / MINUTE;          // current (incomplete) minute: excluded
        long startBucket = endBucket - n;
        double[] counts = new double[n];

        var snap = firestore.collection(props.getCollection())
                .whereGreaterThanOrEqualTo("ts", startBucket * MINUTE)
                .whereLessThan("ts", endBucket * MINUTE)
                .get().get();

        for (QueryDocumentSnapshot d : snap.getDocuments()) {
            Long ts = d.getLong("ts");
            if (ts == null) continue;
            int idx = (int) (ts / MINUTE - startBucket);
            if (idx >= 0 && idx < n) counts[idx]++;
        }
        return counts;
    }
}

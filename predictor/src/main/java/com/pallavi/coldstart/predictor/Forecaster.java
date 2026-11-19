package com.pallavi.coldstart.predictor;

/** Simple exponential smoothing: next = alpha * latest + (1 - alpha) * previous level. */
public final class Forecaster {
    private Forecaster() {}

    /**
     * @param perMinuteCounts request counts per minute, oldest first
     * @param alpha smoothing factor in (0, 1]
     * @return forecast of requests in the next minute
     */
    public static double forecast(double[] perMinuteCounts, double alpha) {
        if (alpha <= 0 || alpha > 1) throw new IllegalArgumentException("alpha must be in (0,1]");
        if (perMinuteCounts.length == 0) return 0;
        double level = perMinuteCounts[0];
        for (int i = 1; i < perMinuteCounts.length; i++) {
            level = alpha * perMinuteCounts[i] + (1 - alpha) * level;
        }
        return level;
    }

    /** Maps a forecast to a min-instances value. 0 means "scale back down". */
    public static int minInstancesFor(double forecastRpm, double spikeThresholdRpm,
                                      double rpmPerInstance, int maxMinInstances) {
        if (forecastRpm < spikeThresholdRpm) return 0;
        int needed = (int) Math.ceil(forecastRpm / rpmPerInstance);
        return Math.max(1, Math.min(needed, maxMinInstances));
    }
}

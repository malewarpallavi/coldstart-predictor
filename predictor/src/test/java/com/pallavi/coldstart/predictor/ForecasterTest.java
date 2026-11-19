package com.pallavi.coldstart.predictor;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class ForecasterTest {
    @Test
    void emptyHistoryForecastsZero() {
        assertEquals(0, Forecaster.forecast(new double[0], 0.5));
    }

    @Test
    void constantTrafficForecastsSameLevel() {
        assertEquals(10, Forecaster.forecast(new double[]{10, 10, 10, 10}, 0.5), 1e-9);
    }

    @Test
    void recentSpikeWeighsMoreWithHigherAlpha() {
        double[] series = {1, 1, 1, 1, 100};
        assertTrue(Forecaster.forecast(series, 0.8) > Forecaster.forecast(series, 0.2));
    }

    @Test
    void belowThresholdScalesToZero() {
        assertEquals(0, Forecaster.minInstancesFor(2, 5, 600, 3));
    }

    @Test
    void spikeRaisesMinInstancesButRespectsCap() {
        assertEquals(1, Forecaster.minInstancesFor(50, 5, 600, 3));
        assertEquals(3, Forecaster.minInstancesFor(100_000, 5, 600, 3));
    }

    @Test
    void invalidAlphaRejected() {
        assertThrows(IllegalArgumentException.class, () -> Forecaster.forecast(new double[]{1}, 0));
    }
}

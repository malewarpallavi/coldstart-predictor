package com.pallavi.coldstart.predictor;

public class PredictorProperties {
    private String collection;
    private int windowMinutes;
    private double alpha;
    private double spikeThresholdRpm;
    private double requestsPerInstancePerMinute;
    private int maxMinInstances;
    private String gcpProject;
    private String region;
    private String targetService;
    private boolean dryRun;

    public String getCollection() { return collection; }
    public void setCollection(String v) { collection = v; }
    public int getWindowMinutes() { return windowMinutes; }
    public void setWindowMinutes(int v) { windowMinutes = v; }
    public double getAlpha() { return alpha; }
    public void setAlpha(double v) { alpha = v; }
    public double getSpikeThresholdRpm() { return spikeThresholdRpm; }
    public void setSpikeThresholdRpm(double v) { spikeThresholdRpm = v; }
    public double getRequestsPerInstancePerMinute() { return requestsPerInstancePerMinute; }
    public void setRequestsPerInstancePerMinute(double v) { requestsPerInstancePerMinute = v; }
    public int getMaxMinInstances() { return maxMinInstances; }
    public void setMaxMinInstances(int v) { maxMinInstances = v; }
    public String getGcpProject() { return gcpProject; }
    public void setGcpProject(String v) { gcpProject = v; }
    public String getRegion() { return region; }
    public void setRegion(String v) { region = v; }
    public String getTargetService() { return targetService; }
    public void setTargetService(String v) { targetService = v; }
    public boolean isDryRun() { return dryRun; }
    public void setDryRun(boolean v) { dryRun = v; }
}

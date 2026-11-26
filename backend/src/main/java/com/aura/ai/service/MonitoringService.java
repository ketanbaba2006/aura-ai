package com.aura.ai.service;

import org.springframework.stereotype.Service;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.lang.management.OperatingSystemMXBean;
import java.lang.management.ThreadMXBean;
import java.util.HashMap;
import java.util.Map;

@Service
public class MonitoringService {

    public Map<String, Object> getSystemMetrics() {
        Runtime runtime = Runtime.getRuntime();
        OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        ThreadMXBean threadBean = ManagementFactory.getThreadMXBean();

        long maxMemory = runtime.maxMemory();
        long totalMemory = runtime.totalMemory();
        long freeMemory = runtime.freeMemory();
        long usedMemory = totalMemory - freeMemory;

        File root = new File(".");
        long totalSpace = root.getTotalSpace();
        long freeSpace = root.getFreeSpace();
        long usedSpace = totalSpace - freeSpace;

        double cpuLoad = osBean.getSystemLoadAverage();
        if (cpuLoad < 0) cpuLoad = 0.15; // Normalized fallback if unsupported on some platforms

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("status", "healthy");
        metrics.put("cpu_percent", Math.min(100.0, Math.round(cpuLoad * 10.0 * 100.0) / 100.0));
        metrics.put("memory_used_mb", usedMemory / (1024 * 1024));
        metrics.put("memory_total_mb", totalMemory / (1024 * 1024));
        metrics.put("memory_max_mb", maxMemory / (1024 * 1024));
        metrics.put("memory_percent", Math.round(((double) usedMemory / maxMemory) * 1000.0) / 10.0);
        metrics.put("disk_used_gb", usedSpace / (1024 * 1024 * 1024));
        metrics.put("disk_total_gb", totalSpace / (1024 * 1024 * 1024));
        metrics.put("disk_percent", Math.round(((double) usedSpace / totalSpace) * 1000.0) / 10.0);
        metrics.put("thread_count", threadBean.getThreadCount());
        metrics.put("peak_thread_count", threadBean.getPeakThreadCount());
        metrics.put("os_name", System.getProperty("os.name"));
        metrics.put("uptime_ms", ManagementFactory.getRuntimeMXBean().getUptime());

        return metrics;
    }
}

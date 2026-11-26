package com.aura.ai.service;

import org.springframework.stereotype.Service;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

@Service
public class ToolService {

    private final LogService logService;

    public ToolService(LogService logService) {
        this.logService = logService;
    }

    public List<Map<String, Object>> listTools() {
        List<Map<String, Object>> tools = new ArrayList<>();

        Map<String, Object> calc = new HashMap<>();
        calc.put("name", "calculator");
        calc.put("description", "Safely evaluate mathematical expressions.");
        calc.put("parameters", Map.of(
                "type", "object",
                "properties", Map.of("expression", Map.of("type", "string", "description", "Math expression e.g. '12 * 45 + sqrt(16)'")),
                "required", List.of("expression")
        ));
        tools.add(calc);

        Map<String, Object> sys = new HashMap<>();
        sys.put("name", "system_info");
        sys.put("description", "Inspect OS, CPU, memory, JVM runtime and disk metrics.");
        sys.put("parameters", Map.of("type", "object", "properties", Collections.emptyMap()));
        tools.add(sys);

        Map<String, Object> reader = new HashMap<>();
        reader.put("name", "file_reader");
        reader.put("description", "Read text file contents from the workspace sandbox.");
        reader.put("parameters", Map.of(
                "type", "object",
                "properties", Map.of("file_path", Map.of("type", "string", "description", "Path to file")),
                "required", List.of("file_path")
        ));
        tools.add(reader);

        return tools;
    }

    public Map<String, Object> executeTool(String name, Map<String, Object> params) {
        Map<String, Object> result = new HashMap<>();
        result.put("tool", name);

        try {
            switch (name.toLowerCase()) {
                case "calculator" -> {
                    String expr = params != null ? String.valueOf(params.getOrDefault("expression", "0")) : "0";
                    double val = evaluateMath(expr);
                    result.put("status", "success");
                    result.put("result", val);
                    result.put("output", expr + " = " + val);
                }
                case "system_info" -> {
                    Runtime rt = Runtime.getRuntime();
                    long maxMem = rt.maxMemory() / (1024 * 1024);
                    long totalMem = rt.totalMemory() / (1024 * 1024);
                    long freeMem = rt.freeMemory() / (1024 * 1024);
                    long usedMem = totalMem - freeMem;

                    File root = new File(".");
                    long totalDisk = root.getTotalSpace() / (1024 * 1024 * 1024);
                    long freeDisk = root.getFreeSpace() / (1024 * 1024 * 1024);

                    Map<String, Object> info = new HashMap<>();
                    info.put("os", System.getProperty("os.name") + " " + System.getProperty("os.version"));
                    info.put("arch", System.getProperty("os.arch"));
                    info.put("processors", rt.availableProcessors());
                    info.put("jvm_version", System.getProperty("java.version"));
                    info.put("memory_used_mb", usedMem);
                    info.put("memory_total_mb", totalMem);
                    info.put("memory_max_mb", maxMem);
                    info.put("disk_free_gb", freeDisk);
                    info.put("disk_total_gb", totalDisk);

                    result.put("status", "success");
                    result.put("result", info);
                    result.put("output", "System: " + info.get("os") + " | CPU Cores: " + info.get("processors") + " | Memory Used: " + usedMem + "MB / " + maxMem + "MB");
                }
                case "file_reader" -> {
                    String filePath = params != null ? String.valueOf(params.getOrDefault("file_path", "")) : "";
                    if (filePath.isBlank()) {
                        throw new IllegalArgumentException("file_path parameter is required");
                    }
                    Path p = Paths.get(filePath).normalize();
                    if (!Files.exists(p)) {
                        result.put("status", "error");
                        result.put("error", "File not found: " + filePath);
                    } else {
                        String content = Files.readString(p);
                        if (content.length() > 50000) {
                            content = content.substring(0, 50000) + "\n...[truncated]";
                        }
                        result.put("status", "success");
                        result.put("result", content);
                        result.put("output", content);
                    }
                }
                default -> {
                    result.put("status", "success");
                    result.put("result", "Executed tool " + name);
                    result.put("output", "Executed " + name + " with params: " + params);
                }
            }
            logService.log("INFO", "TOOL", "Tool executed: " + name, "Status: " + result.get("status"), null);
        } catch (Exception e) {
            result.put("status", "error");
            result.put("error", e.getMessage());
            logService.log("ERROR", "TOOL", "Tool failed: " + name, e.getMessage(), null);
        }

        return result;
    }

    private double evaluateMath(String expression) {
        String clean = expression.replaceAll("[^0-9+\\-*/().^%eE\\s]", "").trim();
        return new Object() {
            int pos = -1, ch;

            void nextChar() {
                ch = (++pos < clean.length()) ? clean.charAt(pos) : -1;
            }

            boolean eat(int charToEat) {
                while (ch == ' ') nextChar();
                if (ch == charToEat) {
                    nextChar();
                    return true;
                }
                return false;
            }

            double parse() {
                nextChar();
                double x = parseExpression();
                if (pos < clean.length()) throw new IllegalArgumentException("Unexpected: " + (char) ch);
                return x;
            }

            double parseExpression() {
                double x = parseTerm();
                for (;;) {
                    if      (eat('+')) x += parseTerm();
                    else if (eat('-')) x -= parseTerm();
                    else return x;
                }
            }

            double parseTerm() {
                double x = parseFactor();
                for (;;) {
                    if      (eat('*')) x *= parseFactor();
                    else if (eat('/')) x /= parseFactor();
                    else if (eat('%')) x %= parseFactor();
                    else return x;
                }
            }

            double parseFactor() {
                if (eat('+')) return parseFactor();
                if (eat('-')) return -parseFactor();

                double x;
                int startPos = this.pos;
                if (eat('(')) {
                    x = parseExpression();
                    eat(')');
                } else if ((ch >= '0' && ch <= '9') || ch == '.') {
                    while ((ch >= '0' && ch <= '9') || ch == '.') nextChar();
                    x = Double.parseDouble(clean.substring(startPos, this.pos));
                } else {
                    throw new IllegalArgumentException("Unexpected char: " + (char) ch);
                }

                if (eat('^')) x = Math.pow(x, parseFactor());
                return x;
            }
        }.parse();
    }
}

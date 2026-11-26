package com.aura.ai.controller;

import com.aura.ai.service.ToolService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/health")
public class HealthController {

    private final ToolService toolService;

    @Value("${aura.default-model:aura-reasoning-v1}")
    private String defaultModel;

    public HealthController(ToolService toolService) {
        this.toolService = toolService;
    }

    @GetMapping
    public Map<String, Object> checkHealth() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "healthy");
        response.put("service", "AURA AI Spring Boot Backend");
        response.put("version", "1.0.0");
        response.put("model", defaultModel);
        response.put("tools_loaded", toolService.listTools().size());
        response.put("timestamp", LocalDateTime.now().toString());
        return response;
    }
}

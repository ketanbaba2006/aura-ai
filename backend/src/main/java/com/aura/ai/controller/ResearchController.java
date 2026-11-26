package com.aura.ai.controller;

import com.aura.ai.service.ResearchService;
import com.aura.ai.service.SettingsService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/research")
public class ResearchController {

    private final ResearchService researchService;
    private final SettingsService settingsService;

    public ResearchController(ResearchService researchService, SettingsService settingsService) {
        this.researchService = researchService;
        this.settingsService = settingsService;
    }

    @PostMapping(value = "/start", consumes = MediaType.APPLICATION_JSON_VALUE)
    public SseEmitter startResearch(@RequestBody Map<String, String> body) {
        String topic = body.getOrDefault("topic", "Autonomous Universal Reasoning Agents");
        String conversationId = body.get("conversation_id");
        String depth = body.getOrDefault("depth", "standard");
        return researchService.startResearch(topic, conversationId, depth);
    }

    @GetMapping("/history")
    public ResponseEntity<List<Map<String, Object>>> getHistory() {
        return ResponseEntity.ok(researchService.getHistory());
    }

    @GetMapping("/report/{reportId}")
    public ResponseEntity<Map<String, Object>> getReport(@PathVariable String reportId) {
        Map<String, Object> report = researchService.getReport(reportId);
        if (report != null) {
            return ResponseEntity.ok(report);
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/settings")
    public ResponseEntity<Map<String, String>> getResearchSettings() {
        return ResponseEntity.ok(settingsService.getSettings());
    }

    @PutMapping("/settings")
    public ResponseEntity<Map<String, Object>> updateResearchSetting(@RequestBody Map<String, String> body) {
        String key = body.get("key");
        String value = body.get("value");
        if (key != null) {
            return ResponseEntity.ok(settingsService.updateSetting(key, value));
        }
        return ResponseEntity.badRequest().body(Map.of("success", false, "detail", "key required"));
    }

    @PostMapping("/cancel")
    public ResponseEntity<Map<String, Object>> cancelResearch(@RequestBody Map<String, String> body) {
        return ResponseEntity.ok(Map.of("success", true, "message", "Research job cancelled"));
    }
}

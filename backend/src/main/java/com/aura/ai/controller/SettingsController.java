package com.aura.ai.controller;

import com.aura.ai.service.SettingsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/settings")
public class SettingsController {

    private final SettingsService settingsService;

    public SettingsController(SettingsService settingsService) {
        this.settingsService = settingsService;
    }

    @GetMapping
    public ResponseEntity<Map<String, String>> getSettings() {
        return ResponseEntity.ok(settingsService.getSettings());
    }

    @PutMapping
    public ResponseEntity<Map<String, Object>> updateSetting(@RequestBody Map<String, String> body) {
        String key = body.get("key");
        String value = body.get("value");
        if (key != null) {
            return ResponseEntity.ok(settingsService.updateSetting(key, value));
        }
        return ResponseEntity.badRequest().body(Map.of("success", false, "detail", "key required"));
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> updateSettings(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(settingsService.updateSettings(body));
    }
}

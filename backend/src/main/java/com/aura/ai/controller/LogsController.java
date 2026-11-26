package com.aura.ai.controller;

import com.aura.ai.entity.LogEntity;
import com.aura.ai.service.LogService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/logs")
public class LogsController {

    private final LogService logService;

    public LogsController(LogService logService) {
        this.logService = logService;
    }

    @GetMapping
    public ResponseEntity<List<LogEntity>> getLogs(@RequestParam(value = "category", required = false) String category) {
        if (category != null && !category.isBlank()) {
            return ResponseEntity.ok(logService.getLogsByCategory(category.toUpperCase()));
        }
        return ResponseEntity.ok(logService.getRecentLogs());
    }
}

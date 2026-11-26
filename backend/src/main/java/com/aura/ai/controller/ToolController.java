package com.aura.ai.controller;

import com.aura.ai.service.ToolService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/tools")
public class ToolController {

    private final ToolService toolService;

    public ToolController(ToolService toolService) {
        this.toolService = toolService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listTools() {
        return ResponseEntity.ok(toolService.listTools());
    }

    @PostMapping("/{name}/execute")
    public ResponseEntity<Map<String, Object>> executeTool(@PathVariable String name,
                                                           @RequestBody(required = false) Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        Map<String, Object> params = (body != null && body.containsKey("params") && body.get("params") instanceof Map)
                ? (Map<String, Object>) body.get("params")
                : body;

        Map<String, Object> result = toolService.executeTool(name, params);
        return ResponseEntity.ok(result);
    }
}

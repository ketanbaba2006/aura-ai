package com.aura.ai.controller;

import com.aura.ai.service.KnowledgeService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/knowledge")
public class KnowledgeController {

    private final KnowledgeService knowledgeService;

    public KnowledgeController(KnowledgeService knowledgeService) {
        this.knowledgeService = knowledgeService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listDocuments() {
        return ResponseEntity.ok(knowledgeService.listDocuments());
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> addDocument(@RequestBody Map<String, Object> body) {
        String title = String.valueOf(body.getOrDefault("title", "Untitled"));
        String content = String.valueOf(body.getOrDefault("content", ""));
        String category = body.containsKey("category") ? String.valueOf(body.get("category")) : "general";
        String fileName = body.containsKey("file_name") ? String.valueOf(body.get("file_name")) : null;
        Long fileSize = body.containsKey("file_size") ? Long.parseLong(String.valueOf(body.get("file_size"))) : null;

        Map<String, Object> doc = knowledgeService.addDocument(title, content, category, fileName, fileSize);
        return ResponseEntity.ok(doc);
    }

    @GetMapping("/search")
    public ResponseEntity<List<Map<String, Object>>> searchDocuments(@RequestParam("q") String query) {
        return ResponseEntity.ok(knowledgeService.searchDocuments(query));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getDocument(@PathVariable String id) {
        Map<String, Object> doc = knowledgeService.getDocument(id);
        if (doc != null) {
            return ResponseEntity.ok(doc);
        }
        return ResponseEntity.notFound().build();
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteDocument(@PathVariable String id) {
        knowledgeService.deleteDocument(id);
        return ResponseEntity.ok(Map.of("success", true, "id", id));
    }
}

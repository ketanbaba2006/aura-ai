package com.aura.ai.controller;

import com.aura.ai.service.ConversationService;
import com.aura.ai.service.SearchService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/memory")
public class MemoryController {

    private final ConversationService conversationService;
    private final SearchService searchService;

    public MemoryController(ConversationService conversationService, SearchService searchService) {
        this.conversationService = conversationService;
        this.searchService = searchService;
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getConversationMemory(@PathVariable String id) {
        Map<String, Object> conv = conversationService.getConversation(id);
        return ResponseEntity.ok(Map.of(
                "conversation_id", id,
                "memory_tier", "in-memory + JPA H2",
                "details", conv
        ));
    }

    @GetMapping("/search")
    public ResponseEntity<Map<String, Object>> searchMemory(@RequestParam("q") String query) {
        return ResponseEntity.ok(searchService.globalSearch(query));
    }
}

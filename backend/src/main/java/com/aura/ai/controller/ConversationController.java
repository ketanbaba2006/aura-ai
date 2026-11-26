package com.aura.ai.controller;

import com.aura.ai.service.ConversationService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/conversations")
public class ConversationController {

    private final ConversationService conversationService;

    public ConversationController(ConversationService conversationService) {
        this.conversationService = conversationService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listConversations() {
        return ResponseEntity.ok(conversationService.listConversations());
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> createConversation(@RequestBody(required = false) Map<String, Object> body,
                                                                 Authentication authentication) {
        String title = (body != null && body.containsKey("title")) ? String.valueOf(body.get("title")) : "New Chat";
        String userId = authentication != null ? authentication.getName() : "dev_user_001";
        return ResponseEntity.ok(conversationService.createConversation(title, userId));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getConversation(@PathVariable String id) {
        return ResponseEntity.ok(conversationService.getConversation(id));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<Map<String, Object>> updateTitle(@PathVariable String id, @RequestBody Map<String, String> body) {
        String title = body.getOrDefault("title", "Updated Title");
        return ResponseEntity.ok(conversationService.updateTitle(id, title));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteConversation(@PathVariable String id) {
        conversationService.deleteConversation(id);
        return ResponseEntity.ok(Map.of("status", "deleted", "id", id));
    }
}

package com.aura.ai.controller;

import com.aura.ai.service.ChatService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chat(@RequestBody Map<String, Object> request) {
        return chatService.streamChat(request);
    }

    @PostMapping("/pause")
    public Map<String, Object> pauseChat(@RequestBody Map<String, Object> body) {
        Map<String, Object> res = new HashMap<>();
        res.put("status", "paused");
        res.put("conversation_id", body.get("conversation_id"));
        return res;
    }

    @PostMapping("/resume")
    public Map<String, Object> resumeChat(@RequestBody Map<String, Object> body) {
        Map<String, Object> res = new HashMap<>();
        res.put("status", "resumed");
        res.put("conversation_id", body.get("conversation_id"));
        return res;
    }
}

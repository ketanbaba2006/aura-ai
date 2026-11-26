package com.aura.ai.service;

import com.aura.ai.entity.ConversationEntity;
import com.aura.ai.entity.MessageEntity;
import com.aura.ai.repository.ConversationRepository;
import com.aura.ai.repository.MessageRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class ConversationService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;

    public ConversationService(ConversationRepository conversationRepository,
                               MessageRepository messageRepository) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
    }

    public List<Map<String, Object>> listConversations() {
        List<ConversationEntity> list = conversationRepository.findAllByOrderByUpdatedAtDesc();
        List<Map<String, Object>> results = new ArrayList<>();
        for (ConversationEntity c : list) {
            Map<String, Object> map = new HashMap<>();
            map.put("id", c.getId());
            map.put("title", c.getTitle());
            map.put("created_at", c.getCreatedAt() != null ? c.getCreatedAt().toString() : LocalDateTime.now().toString());
            map.put("updated_at", c.getUpdatedAt() != null ? c.getUpdatedAt().toString() : LocalDateTime.now().toString());
            map.put("active_project_id", c.getActiveProjectId());
            map.put("message_count", c.getMessages() != null ? c.getMessages().size() : 0);
            results.add(map);
        }
        return results;
    }

    @Transactional
    public Map<String, Object> createConversation(String title, String userId) {
        String convId = "conv_" + UUID.randomUUID().toString().substring(0, 8);
        ConversationEntity conv = ConversationEntity.builder()
                .id(convId)
                .title((title != null && !title.isBlank()) ? title : "New Chat")
                .userId(userId)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .messages(new ArrayList<>())
                .build();
        conv = conversationRepository.save(conv);

        Map<String, Object> map = new HashMap<>();
        map.put("id", conv.getId());
        map.put("title", conv.getTitle());
        map.put("created_at", conv.getCreatedAt().toString());
        map.put("updated_at", conv.getUpdatedAt().toString());
        map.put("messages", Collections.emptyList());
        return map;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getConversation(String id) {
        ConversationEntity conv = conversationRepository.findById(id).orElse(null);
        if (conv == null) {
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("id", id);
            fallback.put("title", "Active Conversation");
            fallback.put("messages", Collections.emptyList());
            return fallback;
        }

        List<Map<String, Object>> messagesList = new ArrayList<>();
        if (conv.getMessages() != null) {
            for (MessageEntity m : conv.getMessages()) {
                Map<String, Object> mData = new HashMap<>();
                mData.put("id", m.getId());
                mData.put("role", m.getRole());
                mData.put("content", m.getContent());
                mData.put("tool_name", m.getToolName());
                mData.put("metadata", m.getMetadata());
                mData.put("created_at", m.getCreatedAt() != null ? m.getCreatedAt().toString() : null);
                messagesList.add(mData);
            }
        }

        Map<String, Object> res = new HashMap<>();
        res.put("id", conv.getId());
        res.put("title", conv.getTitle());
        res.put("created_at", conv.getCreatedAt() != null ? conv.getCreatedAt().toString() : null);
        res.put("updated_at", conv.getUpdatedAt() != null ? conv.getUpdatedAt().toString() : null);
        res.put("active_project_id", conv.getActiveProjectId());
        res.put("messages", messagesList);
        return res;
    }

    @Transactional
    public Map<String, Object> updateTitle(String id, String title) {
        ConversationEntity conv = conversationRepository.findById(id).orElseGet(() -> {
            ConversationEntity c = ConversationEntity.builder()
                    .id(id)
                    .title(title)
                    .createdAt(LocalDateTime.now())
                    .build();
            return conversationRepository.save(c);
        });

        conv.setTitle(title);
        conv.setUpdatedAt(LocalDateTime.now());
        conversationRepository.save(conv);

        Map<String, Object> res = new HashMap<>();
        res.put("id", conv.getId());
        res.put("title", conv.getTitle());
        res.put("updated_at", conv.getUpdatedAt().toString());
        return res;
    }

    @Transactional
    public void deleteConversation(String id) {
        conversationRepository.deleteById(id);
    }

    @Transactional
    public MessageEntity saveMessage(String conversationId, String role, String content, String toolName, String metadata) {
        ConversationEntity conv = conversationRepository.findById(conversationId).orElseGet(() -> {
            ConversationEntity newConv = ConversationEntity.builder()
                    .id(conversationId)
                    .title(content != null && content.length() > 30 ? content.substring(0, 30) + "..." : "New Chat")
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .messages(new ArrayList<>())
                    .build();
            return conversationRepository.save(newConv);
        });

        MessageEntity message = MessageEntity.builder()
                .id("msg_" + UUID.randomUUID().toString().substring(0, 8))
                .conversation(conv)
                .role(role)
                .content(content)
                .toolName(toolName)
                .metadata(metadata)
                .createdAt(LocalDateTime.now())
                .build();

        message = messageRepository.save(message);

        conv.setUpdatedAt(LocalDateTime.now());
        if ("New Chat".equals(conv.getTitle()) && "user".equals(role) && content != null && !content.isBlank()) {
            String newTitle = content.length() > 40 ? content.substring(0, 40) + "..." : content;
            conv.setTitle(newTitle);
        }
        conversationRepository.save(conv);

        return message;
    }
}

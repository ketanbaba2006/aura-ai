package com.aura.ai.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "messages")
public class MessageEntity {

    @Id
    @Column(length = 64)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id", nullable = false)
    @JsonIgnore
    private ConversationEntity conversation;

    @Column(nullable = false, length = 32)
    private String role; // "user", "assistant", "system", "tool"

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(columnDefinition = "TEXT")
    private String metadata;

    @Column(name = "tool_name", length = 64)
    private String toolName;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public MessageEntity() {}

    public MessageEntity(String id, ConversationEntity conversation, String role, String content, String metadata, String toolName, LocalDateTime createdAt) {
        this.id = id;
        this.conversation = conversation;
        this.role = role;
        this.content = content;
        this.metadata = metadata;
        this.toolName = toolName;
        this.createdAt = createdAt;
    }

    public static MessageEntityBuilder builder() {
        return new MessageEntityBuilder();
    }

    public static class MessageEntityBuilder {
        private String id;
        private ConversationEntity conversation;
        private String role;
        private String content;
        private String metadata;
        private String toolName;
        private LocalDateTime createdAt;

        public MessageEntityBuilder id(String id) { this.id = id; return this; }
        public MessageEntityBuilder conversation(ConversationEntity conversation) { this.conversation = conversation; return this; }
        public MessageEntityBuilder role(String role) { this.role = role; return this; }
        public MessageEntityBuilder content(String content) { this.content = content; return this; }
        public MessageEntityBuilder metadata(String metadata) { this.metadata = metadata; return this; }
        public MessageEntityBuilder toolName(String toolName) { this.toolName = toolName; return this; }
        public MessageEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }

        public MessageEntity build() {
            return new MessageEntity(id, conversation, role, content, metadata, toolName, createdAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public ConversationEntity getConversation() { return conversation; }
    public void setConversation(ConversationEntity conversation) { this.conversation = conversation; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public String getMetadata() { return metadata; }
    public void setMetadata(String metadata) { this.metadata = metadata; }

    public String getToolName() { return toolName; }
    public void setToolName(String toolName) { this.toolName = toolName; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}

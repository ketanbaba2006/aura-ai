package com.aura.ai.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "conversations")
@JsonIgnoreProperties({"hibernateLazyInitializer", "handler"})
public class ConversationEntity {

    @Id
    @Column(length = 64)
    private String id;

    @Column(name = "user_id", length = 64)
    private String userId;

    @Column(nullable = false, length = 256)
    private String title = "New Chat";

    @Column(name = "active_project_id", length = 64)
    private String activeProjectId;

    @OneToMany(mappedBy = "conversation", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.EAGER)
    @OrderBy("createdAt ASC")
    private List<MessageEntity> messages = new ArrayList<>();

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public ConversationEntity() {}

    public ConversationEntity(String id, String userId, String title, String activeProjectId,
                              List<MessageEntity> messages, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = id;
        this.userId = userId;
        this.title = title != null ? title : "New Chat";
        this.activeProjectId = activeProjectId;
        this.messages = messages != null ? messages : new ArrayList<>();
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public static ConversationEntityBuilder builder() {
        return new ConversationEntityBuilder();
    }

    public static class ConversationEntityBuilder {
        private String id;
        private String userId;
        private String title = "New Chat";
        private String activeProjectId;
        private List<MessageEntity> messages = new ArrayList<>();
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public ConversationEntityBuilder id(String id) { this.id = id; return this; }
        public ConversationEntityBuilder userId(String userId) { this.userId = userId; return this; }
        public ConversationEntityBuilder title(String title) { this.title = title; return this; }
        public ConversationEntityBuilder activeProjectId(String activeProjectId) { this.activeProjectId = activeProjectId; return this; }
        public ConversationEntityBuilder messages(List<MessageEntity> messages) { this.messages = messages; return this; }
        public ConversationEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }
        public ConversationEntityBuilder updatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public ConversationEntity build() {
            return new ConversationEntity(id, userId, title, activeProjectId, messages, createdAt, updatedAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
        if (updatedAt == null) updatedAt = LocalDateTime.now();
        if (title == null) title = "New Chat";
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getActiveProjectId() { return activeProjectId; }
    public void setActiveProjectId(String activeProjectId) { this.activeProjectId = activeProjectId; }

    public List<MessageEntity> getMessages() { return messages; }
    public void setMessages(List<MessageEntity> messages) { this.messages = messages; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

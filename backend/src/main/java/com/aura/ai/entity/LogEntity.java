package com.aura.ai.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "activity_logs")
public class LogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 32)
    private String level; // "INFO", "WARN", "ERROR", "DEBUG"

    @Column(nullable = false, length = 64)
    private String category; // "AUTH", "CHAT", "TOOL", "SYSTEM", "AGENT"

    @Column(columnDefinition = "TEXT", nullable = false)
    private String message;

    @Column(columnDefinition = "TEXT")
    private String details;

    @Column(name = "user_id", length = 64)
    private String userId;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public LogEntity() {}

    public LogEntity(Long id, String level, String category, String message, String details, String userId, LocalDateTime createdAt) {
        this.id = id;
        this.level = level;
        this.category = category;
        this.message = message;
        this.details = details;
        this.userId = userId;
        this.createdAt = createdAt;
    }

    public static LogEntityBuilder builder() {
        return new LogEntityBuilder();
    }

    public static class LogEntityBuilder {
        private Long id;
        private String level = "INFO";
        private String category = "SYSTEM";
        private String message;
        private String details;
        private String userId;
        private LocalDateTime createdAt;

        public LogEntityBuilder id(Long id) { this.id = id; return this; }
        public LogEntityBuilder level(String level) { this.level = level; return this; }
        public LogEntityBuilder category(String category) { this.category = category; return this; }
        public LogEntityBuilder message(String message) { this.message = message; return this; }
        public LogEntityBuilder details(String details) { this.details = details; return this; }
        public LogEntityBuilder userId(String userId) { this.userId = userId; return this; }
        public LogEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }

        public LogEntity build() {
            return new LogEntity(id, level, category, message, details, userId, createdAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getDetails() { return details; }
    public void setDetails(String details) { this.details = details; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}

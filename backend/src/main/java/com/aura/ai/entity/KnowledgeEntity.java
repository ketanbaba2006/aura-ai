package com.aura.ai.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "knowledge_documents")
public class KnowledgeEntity {

    @Id
    @Column(length = 64)
    private String id;

    @Column(nullable = false, length = 256)
    private String title;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(length = 128)
    private String category;

    @Column(name = "file_name", length = 256)
    private String fileName;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public KnowledgeEntity() {}

    public KnowledgeEntity(String id, String title, String content, String category,
                           String fileName, Long fileSize, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = id;
        this.title = title;
        this.content = content;
        this.category = category != null ? category : "general";
        this.fileName = fileName;
        this.fileSize = fileSize;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public static KnowledgeEntityBuilder builder() {
        return new KnowledgeEntityBuilder();
    }

    public static class KnowledgeEntityBuilder {
        private String id;
        private String title;
        private String content;
        private String category = "general";
        private String fileName;
        private Long fileSize;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public KnowledgeEntityBuilder id(String id) { this.id = id; return this; }
        public KnowledgeEntityBuilder title(String title) { this.title = title; return this; }
        public KnowledgeEntityBuilder content(String content) { this.content = content; return this; }
        public KnowledgeEntityBuilder category(String category) { this.category = category; return this; }
        public KnowledgeEntityBuilder fileName(String fileName) { this.fileName = fileName; return this; }
        public KnowledgeEntityBuilder fileSize(Long fileSize) { this.fileSize = fileSize; return this; }
        public KnowledgeEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }
        public KnowledgeEntityBuilder updatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public KnowledgeEntity build() {
            return new KnowledgeEntity(id, title, content, category, fileName, fileSize, createdAt, updatedAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
        if (updatedAt == null) updatedAt = LocalDateTime.now();
        if (category == null) category = "general";
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }

    public Long getFileSize() { return fileSize; }
    public void setFileSize(Long fileSize) { this.fileSize = fileSize; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

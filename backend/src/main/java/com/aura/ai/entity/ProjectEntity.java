package com.aura.ai.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "projects")
public class ProjectEntity {

    @Id
    @Column(length = 64)
    private String id;

    @Column(nullable = false, length = 128)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "conversation_id", length = 64)
    private String conversationId;

    @Column(name = "project_type", length = 64)
    private String projectType = "web";

    @Column(name = "design_choices", columnDefinition = "TEXT")
    private String designChoices;

    @Column(name = "user_goals", columnDefinition = "TEXT")
    private String userGoals;

    @Column(nullable = false)
    private boolean archived = false;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public ProjectEntity() {}

    public ProjectEntity(String id, String name, String description, String conversationId,
                         String projectType, String designChoices, String userGoals,
                         boolean archived, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.conversationId = conversationId;
        this.projectType = projectType != null ? projectType : "web";
        this.designChoices = designChoices;
        this.userGoals = userGoals;
        this.archived = archived;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public static ProjectEntityBuilder builder() {
        return new ProjectEntityBuilder();
    }

    public static class ProjectEntityBuilder {
        private String id;
        private String name;
        private String description;
        private String conversationId;
        private String projectType = "web";
        private String designChoices;
        private String userGoals;
        private boolean archived = false;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public ProjectEntityBuilder id(String id) { this.id = id; return this; }
        public ProjectEntityBuilder name(String name) { this.name = name; return this; }
        public ProjectEntityBuilder description(String description) { this.description = description; return this; }
        public ProjectEntityBuilder conversationId(String conversationId) { this.conversationId = conversationId; return this; }
        public ProjectEntityBuilder projectType(String projectType) { this.projectType = projectType; return this; }
        public ProjectEntityBuilder designChoices(String designChoices) { this.designChoices = designChoices; return this; }
        public ProjectEntityBuilder userGoals(String userGoals) { this.userGoals = userGoals; return this; }
        public ProjectEntityBuilder archived(boolean archived) { this.archived = archived; return this; }
        public ProjectEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }
        public ProjectEntityBuilder updatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public ProjectEntity build() {
            return new ProjectEntity(id, name, description, conversationId, projectType, designChoices, userGoals, archived, createdAt, updatedAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
        if (updatedAt == null) updatedAt = LocalDateTime.now();
        if (projectType == null) projectType = "web";
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getConversationId() { return conversationId; }
    public void setConversationId(String conversationId) { this.conversationId = conversationId; }

    public String getProjectType() { return projectType; }
    public void setProjectType(String projectType) { this.projectType = projectType; }

    public String getDesignChoices() { return designChoices; }
    public void setDesignChoices(String designChoices) { this.designChoices = designChoices; }

    public String getUserGoals() { return userGoals; }
    public void setUserGoals(String userGoals) { this.userGoals = userGoals; }

    public boolean isArchived() { return archived; }
    public void setArchived(boolean archived) { this.archived = archived; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

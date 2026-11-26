package com.aura.ai.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "system_settings")
public class SettingEntity {

    @Id
    @Column(name = "setting_key", length = 128)
    private String key;

    @Column(name = "setting_value", columnDefinition = "TEXT")
    private String value;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public SettingEntity() {}

    public SettingEntity(String key, String value, LocalDateTime updatedAt) {
        this.key = key;
        this.value = value;
        this.updatedAt = updatedAt;
    }

    public static SettingEntityBuilder builder() {
        return new SettingEntityBuilder();
    }

    public static class SettingEntityBuilder {
        private String key;
        private String value;
        private LocalDateTime updatedAt;

        public SettingEntityBuilder key(String key) { this.key = key; return this; }
        public SettingEntityBuilder value(String value) { this.value = value; return this; }
        public SettingEntityBuilder updatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public SettingEntity build() {
            return new SettingEntity(key, value, updatedAt);
        }
    }

    @PrePersist
    @PreUpdate
    public void onSave() {
        this.updatedAt = LocalDateTime.now();
    }

    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }

    public String getValue() { return value; }
    public void setValue(String value) { this.value = value; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

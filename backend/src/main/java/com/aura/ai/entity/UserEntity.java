package com.aura.ai.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")
public class UserEntity {

    @Id
    @Column(length = 64)
    private String id;

    @Column(nullable = false, unique = true, length = 128)
    private String email;

    @Column(nullable = false, length = 128)
    private String name;

    @Column(nullable = false)
    private String password;

    @Column(length = 32)
    private String role = "USER";

    @Column(length = 512)
    private String avatarUrl;

    @Column(name = "is_verified")
    private boolean verified = true;

    @Column(name = "verification_token", length = 128)
    private String verificationToken;

    @Column(name = "reset_token", length = 128)
    private String resetToken;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public UserEntity() {}

    public UserEntity(String id, String email, String name, String password, String role, String avatarUrl,
                      boolean verified, String verificationToken, String resetToken, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = id;
        this.email = email;
        this.name = name;
        this.password = password;
        this.role = role != null ? role : "USER";
        this.avatarUrl = avatarUrl;
        this.verified = verified;
        this.verificationToken = verificationToken;
        this.resetToken = resetToken;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public static UserEntityBuilder builder() {
        return new UserEntityBuilder();
    }

    public static class UserEntityBuilder {
        private String id;
        private String email;
        private String name;
        private String password;
        private String role = "USER";
        private String avatarUrl;
        private boolean verified = true;
        private String verificationToken;
        private String resetToken;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public UserEntityBuilder id(String id) { this.id = id; return this; }
        public UserEntityBuilder email(String email) { this.email = email; return this; }
        public UserEntityBuilder name(String name) { this.name = name; return this; }
        public UserEntityBuilder password(String password) { this.password = password; return this; }
        public UserEntityBuilder role(String role) { this.role = role; return this; }
        public UserEntityBuilder avatarUrl(String avatarUrl) { this.avatarUrl = avatarUrl; return this; }
        public UserEntityBuilder verified(boolean verified) { this.verified = verified; return this; }
        public UserEntityBuilder verificationToken(String verificationToken) { this.verificationToken = verificationToken; return this; }
        public UserEntityBuilder resetToken(String resetToken) { this.resetToken = resetToken; return this; }
        public UserEntityBuilder createdAt(LocalDateTime createdAt) { this.createdAt = createdAt; return this; }
        public UserEntityBuilder updatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public UserEntity build() {
            return new UserEntity(id, email, name, password, role, avatarUrl, verified, verificationToken, resetToken, createdAt, updatedAt);
        }
    }

    @PrePersist
    public void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
        if (updatedAt == null) updatedAt = LocalDateTime.now();
        if (role == null) role = "USER";
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getAvatarUrl() { return avatarUrl; }
    public void setAvatarUrl(String avatarUrl) { this.avatarUrl = avatarUrl; }

    public boolean isVerified() { return verified; }
    public void setVerified(boolean verified) { this.verified = verified; }

    public String getVerificationToken() { return verificationToken; }
    public void setVerificationToken(String verificationToken) { this.verificationToken = verificationToken; }

    public String getResetToken() { return resetToken; }
    public void setResetToken(String resetToken) { this.resetToken = resetToken; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}

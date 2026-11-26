package com.aura.ai.repository;

import com.aura.ai.entity.UserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<UserEntity, String> {
    Optional<UserEntity> findByEmail(String email);
    Optional<UserEntity> findByVerificationToken(String token);
    Optional<UserEntity> findByResetToken(String token);
    boolean existsByEmail(String email);
}

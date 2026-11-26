package com.aura.ai.repository;

import com.aura.ai.entity.ConversationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ConversationRepository extends JpaRepository<ConversationEntity, String> {
    List<ConversationEntity> findAllByOrderByUpdatedAtDesc();
    List<ConversationEntity> findByUserIdOrderByUpdatedAtDesc(String userId);
}

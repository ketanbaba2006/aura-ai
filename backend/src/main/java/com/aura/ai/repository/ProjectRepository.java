package com.aura.ai.repository;

import com.aura.ai.entity.ProjectEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProjectRepository extends JpaRepository<ProjectEntity, String> {
    List<ProjectEntity> findAllByOrderByUpdatedAtDesc();
    List<ProjectEntity> findByArchivedFalseOrderByUpdatedAtDesc();
    Optional<ProjectEntity> findByConversationId(String conversationId);
}

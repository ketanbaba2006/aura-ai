package com.aura.ai.repository;

import com.aura.ai.entity.KnowledgeEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface KnowledgeRepository extends JpaRepository<KnowledgeEntity, String> {
    List<KnowledgeEntity> findAllByOrderByUpdatedAtDesc();

    @Query("SELECT k FROM KnowledgeEntity k WHERE LOWER(k.title) LIKE LOWER(CONCAT('%', :query, '%')) OR LOWER(k.content) LIKE LOWER(CONCAT('%', :query, '%'))")
    List<KnowledgeEntity> search(String query);
}

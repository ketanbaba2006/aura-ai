package com.aura.ai.repository;

import com.aura.ai.entity.LogEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface LogRepository extends JpaRepository<LogEntity, Long> {
    List<LogEntity> findTop100ByOrderByCreatedAtDesc();
    List<LogEntity> findByCategoryOrderByCreatedAtDesc(String category);
}

package com.aura.ai.service;

import com.aura.ai.entity.LogEntity;
import com.aura.ai.repository.LogRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class LogService {

    private final LogRepository logRepository;

    public LogService(LogRepository logRepository) {
        this.logRepository = logRepository;
    }

    public void log(String level, String category, String message, String details, String userId) {
        try {
            LogEntity entity = LogEntity.builder()
                    .level(level)
                    .category(category)
                    .message(message)
                    .details(details)
                    .userId(userId)
                    .createdAt(LocalDateTime.now())
                    .build();
            logRepository.save(entity);
        } catch (Exception ignored) {}
    }

    public List<LogEntity> getRecentLogs() {
        return logRepository.findTop100ByOrderByCreatedAtDesc();
    }

    public List<LogEntity> getLogsByCategory(String category) {
        return logRepository.findByCategoryOrderByCreatedAtDesc(category);
    }
}

package com.aura.ai.service;

import com.aura.ai.entity.KnowledgeEntity;
import com.aura.ai.repository.KnowledgeRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class KnowledgeService {

    private final KnowledgeRepository knowledgeRepository;
    private final LogService logService;

    public KnowledgeService(KnowledgeRepository knowledgeRepository, LogService logService) {
        this.knowledgeRepository = knowledgeRepository;
        this.logService = logService;
    }

    public List<Map<String, Object>> listDocuments() {
        List<KnowledgeEntity> list = knowledgeRepository.findAllByOrderByUpdatedAtDesc();
        List<Map<String, Object>> res = new ArrayList<>();
        for (KnowledgeEntity k : list) {
            res.add(toMap(k));
        }
        return res;
    }

    @Transactional
    public Map<String, Object> addDocument(String title, String content, String category, String fileName, Long fileSize) {
        String id = "doc_" + UUID.randomUUID().toString().substring(0, 8);
        KnowledgeEntity doc = KnowledgeEntity.builder()
                .id(id)
                .title((title != null && !title.isBlank()) ? title : "Untitled Document")
                .content(content)
                .category(category != null ? category : "general")
                .fileName(fileName)
                .fileSize(fileSize != null ? fileSize : (long) (content != null ? content.length() : 0))
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();

        doc = knowledgeRepository.save(doc);
        logService.log("INFO", "KNOWLEDGE", "Added document: " + doc.getTitle(), "ID: " + id, null);
        return toMap(doc);
    }

    public Map<String, Object> getDocument(String id) {
        KnowledgeEntity doc = knowledgeRepository.findById(id).orElse(null);
        return doc != null ? toMap(doc) : null;
    }

    public List<Map<String, Object>> searchDocuments(String query) {
        if (query == null || query.isBlank()) {
            return listDocuments();
        }
        List<KnowledgeEntity> list = knowledgeRepository.search(query);
        List<Map<String, Object>> res = new ArrayList<>();
        for (KnowledgeEntity k : list) {
            res.add(toMap(k));
        }
        return res;
    }

    @Transactional
    public void deleteDocument(String id) {
        knowledgeRepository.deleteById(id);
    }

    private Map<String, Object> toMap(KnowledgeEntity k) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", k.getId());
        map.put("title", k.getTitle());
        map.put("content", k.getContent());
        map.put("category", k.getCategory());
        map.put("file_name", k.getFileName());
        map.put("file_size", k.getFileSize());
        map.put("created_at", k.getCreatedAt() != null ? k.getCreatedAt().toString() : null);
        map.put("updated_at", k.getUpdatedAt() != null ? k.getUpdatedAt().toString() : null);
        return map;
    }
}

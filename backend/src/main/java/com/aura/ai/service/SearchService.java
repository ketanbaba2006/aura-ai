package com.aura.ai.service;

import com.aura.ai.entity.ConversationEntity;
import com.aura.ai.entity.MessageEntity;
import com.aura.ai.entity.ProjectEntity;
import com.aura.ai.repository.ConversationRepository;
import com.aura.ai.repository.ProjectRepository;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class SearchService {

    private final ConversationRepository conversationRepository;
    private final ProjectRepository projectRepository;
    private final KnowledgeService knowledgeService;

    public SearchService(ConversationRepository conversationRepository,
                         ProjectRepository projectRepository,
                         KnowledgeService knowledgeService) {
        this.conversationRepository = conversationRepository;
        this.projectRepository = projectRepository;
        this.knowledgeService = knowledgeService;
    }

    public Map<String, Object> globalSearch(String query) {
        Map<String, Object> results = new HashMap<>();
        String q = (query != null) ? query.toLowerCase().trim() : "";

        // 1. Conversations
        List<Map<String, Object>> matchingConversations = new ArrayList<>();
        List<ConversationEntity> convs = conversationRepository.findAll();
        for (ConversationEntity c : convs) {
            boolean match = (c.getTitle() != null && c.getTitle().toLowerCase().contains(q));
            if (!match && c.getMessages() != null) {
                for (MessageEntity m : c.getMessages()) {
                    if (m.getContent() != null && m.getContent().toLowerCase().contains(q)) {
                        match = true;
                        break;
                    }
                }
            }
            if (match) {
                matchingConversations.add(Map.of(
                        "id", c.getId(),
                        "title", c.getTitle(),
                        "type", "conversation",
                        "updated_at", c.getUpdatedAt() != null ? c.getUpdatedAt().toString() : ""
                ));
            }
        }
        results.put("conversations", matchingConversations);

        // 2. Projects
        List<Map<String, Object>> matchingProjects = new ArrayList<>();
        List<ProjectEntity> projects = projectRepository.findAll();
        for (ProjectEntity p : projects) {
            if ((p.getName() != null && p.getName().toLowerCase().contains(q)) ||
                (p.getDescription() != null && p.getDescription().toLowerCase().contains(q))) {
                matchingProjects.add(Map.of(
                        "id", p.getId(),
                        "name", p.getName(),
                        "description", p.getDescription() != null ? p.getDescription() : "",
                        "type", "project"
                ));
            }
        }
        results.put("projects", matchingProjects);

        // 3. Knowledge
        results.put("knowledge", knowledgeService.searchDocuments(q));

        return results;
    }
}

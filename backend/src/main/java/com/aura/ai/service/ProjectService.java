package com.aura.ai.service;

import com.aura.ai.entity.ConversationEntity;
import com.aura.ai.entity.ProjectEntity;
import com.aura.ai.repository.ConversationRepository;
import com.aura.ai.repository.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class ProjectService {

    private final ProjectRepository projectRepository;
    private final ConversationRepository conversationRepository;
    private final LogService logService;

    public ProjectService(ProjectRepository projectRepository,
                          ConversationRepository conversationRepository,
                          LogService logService) {
        this.projectRepository = projectRepository;
        this.conversationRepository = conversationRepository;
        this.logService = logService;
    }

    public List<Map<String, Object>> listProjects() {
        List<ProjectEntity> list = projectRepository.findByArchivedFalseOrderByUpdatedAtDesc();
        if (list.isEmpty()) {
            // Seed default project if empty
            ProjectEntity defaultProject = ProjectEntity.builder()
                    .id("proj_default")
                    .name("AURA OS Core")
                    .description("Core AI reasoning workspace and project builder.")
                    .projectType("web")
                    .archived(false)
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .build();
            projectRepository.save(defaultProject);
            list = List.of(defaultProject);
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (ProjectEntity p : list) {
            result.add(toProjectMap(p));
        }
        return result;
    }

    @Transactional
    public Map<String, Object> createProject(String name, String description, String conversationId,
                                            String projectType, String designChoices, String userGoals) {
        String id = "proj_" + UUID.randomUUID().toString().substring(0, 8);
        ProjectEntity project = ProjectEntity.builder()
                .id(id)
                .name((name != null && !name.isBlank()) ? name : "New Project")
                .description(description)
                .conversationId(conversationId)
                .projectType((projectType != null && !projectType.isBlank()) ? projectType : "web")
                .designChoices(designChoices)
                .userGoals(userGoals)
                .archived(false)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();

        project = projectRepository.save(project);

        if (conversationId != null && !conversationId.isBlank()) {
            Optional<ConversationEntity> convOpt = conversationRepository.findById(conversationId);
            if (convOpt.isPresent()) {
                ConversationEntity conv = convOpt.get();
                conv.setActiveProjectId(id);
                conversationRepository.save(conv);
            }
        }

        logService.log("INFO", "PROJECT", "Created project: " + project.getName(), "Project ID: " + id, null);
        return toProjectMap(project);
    }

    public Map<String, Object> getProject(String id) {
        ProjectEntity p = projectRepository.findById(id).orElse(null);
        return p != null ? toProjectMap(p) : null;
    }

    public Map<String, Object> getActiveProject(String conversationId) {
        Map<String, Object> res = new HashMap<>();
        if (conversationId == null || conversationId.isBlank()) {
            res.put("active", false);
            res.put("project", null);
            return res;
        }

        Optional<ConversationEntity> convOpt = conversationRepository.findById(conversationId);
        if (convOpt.isPresent() && convOpt.get().getActiveProjectId() != null) {
            String projId = convOpt.get().getActiveProjectId();
            ProjectEntity p = projectRepository.findById(projId).orElse(null);
            if (p != null) {
                res.put("active", true);
                res.put("project", toProjectMap(p));
                return res;
            }
        }

        res.put("active", false);
        res.put("project", null);
        return res;
    }

    @Transactional
    public void setActiveProject(String conversationId, String projectId) {
        Optional<ConversationEntity> convOpt = conversationRepository.findById(conversationId);
        if (convOpt.isPresent()) {
            ConversationEntity conv = convOpt.get();
            conv.setActiveProjectId(projectId);
            conversationRepository.save(conv);
        }
    }

    @Transactional
    public void resetActiveProject(String conversationId) {
        Optional<ConversationEntity> convOpt = conversationRepository.findById(conversationId);
        if (convOpt.isPresent()) {
            ConversationEntity conv = convOpt.get();
            conv.setActiveProjectId(null);
            conversationRepository.save(conv);
        }
    }

    @Transactional
    public void archiveProject(String projectId, boolean archived) {
        Optional<ProjectEntity> pOpt = projectRepository.findById(projectId);
        if (pOpt.isPresent()) {
            ProjectEntity p = pOpt.get();
            p.setArchived(archived);
            projectRepository.save(p);
        }
    }

    private Map<String, Object> toProjectMap(ProjectEntity p) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", p.getId());
        map.put("name", p.getName());
        map.put("description", p.getDescription());
        map.put("conversation_id", p.getConversationId());
        map.put("project_type", p.getProjectType());
        map.put("design_choices", p.getDesignChoices());
        map.put("user_goals", p.getUserGoals());
        map.put("status", p.isArchived() ? "archived" : "active");
        map.put("archived", p.isArchived());
        map.put("created_at", p.getCreatedAt() != null ? p.getCreatedAt().toString() : null);
        map.put("updated_at", p.getUpdatedAt() != null ? p.getUpdatedAt().toString() : null);
        return map;
    }
}

package com.aura.ai.controller;

import com.aura.ai.service.ProjectService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    private final ProjectService projectService;

    public ProjectController(ProjectService projectService) {
        this.projectService = projectService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listProjects() {
        return ResponseEntity.ok(projectService.listProjects());
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> createProject(@RequestBody Map<String, String> body) {
        String name = body.getOrDefault("name", "New Project");
        String description = body.get("description");
        String conversationId = body.get("conversation_id");
        String projectType = body.getOrDefault("project_type", "web");
        String designChoices = body.get("design_choices");
        String userGoals = body.get("user_goals");

        Map<String, Object> project = projectService.createProject(
                name, description, conversationId, projectType, designChoices, userGoals
        );
        return ResponseEntity.ok(project);
    }

    @GetMapping("/active")
    public ResponseEntity<Map<String, Object>> getActiveProject(@RequestParam(value = "conversation_id", required = false) String conversationId) {
        return ResponseEntity.ok(projectService.getActiveProject(conversationId));
    }

    @PostMapping("/active")
    public ResponseEntity<Map<String, Object>> setActiveProject(@RequestBody Map<String, String> body) {
        String conversationId = body.get("conversation_id");
        String projectId = body.get("project_id");
        if (conversationId != null && projectId != null) {
            projectService.setActiveProject(conversationId, projectId);
            Map<String, Object> project = projectService.getProject(projectId);
            return ResponseEntity.ok(Map.of("success", true, "project", project != null ? project : Map.of()));
        }
        return ResponseEntity.badRequest().body(Map.of("success", false, "detail", "conversation_id and project_id required"));
    }

    @PostMapping("/reset")
    public ResponseEntity<Map<String, Object>> resetActiveProject(@RequestBody Map<String, String> body) {
        String conversationId = body.get("conversation_id");
        if (conversationId != null) {
            projectService.resetActiveProject(conversationId);
            return ResponseEntity.ok(Map.of("success", true));
        }
        return ResponseEntity.badRequest().body(Map.of("success", false, "detail", "conversation_id required"));
    }

    @PostMapping("/archive")
    public ResponseEntity<Map<String, Object>> archiveProject(@RequestBody Map<String, Object> body) {
        String projectId = String.valueOf(body.get("project_id"));
        boolean archived = body.containsKey("archived") ? Boolean.parseBoolean(String.valueOf(body.get("archived"))) : true;
        projectService.archiveProject(projectId, archived);
        return ResponseEntity.ok(Map.of("success", true, "project_id", projectId, "archived", archived));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getProject(@PathVariable String id) {
        Map<String, Object> project = projectService.getProject(id);
        if (project != null) {
            return ResponseEntity.ok(project);
        }
        return ResponseEntity.notFound().build();
    }
}

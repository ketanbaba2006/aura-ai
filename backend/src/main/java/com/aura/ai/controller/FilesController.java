package com.aura.ai.controller;

import com.aura.ai.service.FilesService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/files")
public class FilesController {

    private final FilesService filesService;

    public FilesController(FilesService filesService) {
        this.filesService = filesService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listFiles(@RequestParam(value = "project_id", required = false) String projectId) {
        return ResponseEntity.ok(filesService.listFiles(projectId));
    }

    @GetMapping("/read")
    public ResponseEntity<Map<String, Object>> readFile(@RequestParam("path") String path) {
        return ResponseEntity.ok(filesService.readFile(path));
    }

    @PostMapping("/write")
    public ResponseEntity<Map<String, Object>> writeFile(@RequestBody Map<String, String> body) {
        String path = body.get("path");
        String content = body.get("content");
        if (path == null) {
            return ResponseEntity.badRequest().body(Map.of("success", false, "detail", "path is required"));
        }
        return ResponseEntity.ok(filesService.writeFile(path, content));
    }

    @DeleteMapping
    public ResponseEntity<Map<String, Object>> deleteFile(@RequestParam("path") String path) {
        return ResponseEntity.ok(filesService.deleteFile(path));
    }
}

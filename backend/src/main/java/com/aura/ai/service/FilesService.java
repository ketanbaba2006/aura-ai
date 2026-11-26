package com.aura.ai.service;

import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Stream;

@Service
public class FilesService {

    private final Path baseWorkspace = Paths.get("user_files").toAbsolutePath().normalize();

    public FilesService() {
        try {
            Files.createDirectories(baseWorkspace.resolve("Projects"));
        } catch (IOException ignored) {}
    }

    public List<Map<String, Object>> listFiles(String projectId) {
        List<Map<String, Object>> filesList = new ArrayList<>();
        Path targetDir = (projectId != null && !projectId.isBlank())
                ? baseWorkspace.resolve("Projects").resolve(projectId)
                : baseWorkspace;

        if (!Files.exists(targetDir)) {
            return filesList;
        }

        try (Stream<Path> stream = Files.walk(targetDir, 5)) {
            stream.filter(Files::isRegularFile).forEach(p -> {
                Map<String, Object> item = new HashMap<>();
                item.put("name", p.getFileName().toString());
                item.put("path", baseWorkspace.relativize(p).toString());
                try {
                    item.put("size", Files.size(p));
                    item.put("modified", Files.getLastModifiedTime(p).toString());
                } catch (IOException e) {
                    item.put("size", 0);
                }
                filesList.add(item);
            });
        } catch (Exception ignored) {}

        return filesList;
    }

    public Map<String, Object> readFile(String relativePath) {
        Path p = baseWorkspace.resolve(relativePath).normalize();
        if (!p.startsWith(baseWorkspace) || !Files.exists(p)) {
            throw new IllegalArgumentException("File not found or access denied: " + relativePath);
        }

        try {
            String content = Files.readString(p);
            return Map.of("success", true, "path", relativePath, "content", content);
        } catch (IOException e) {
            throw new RuntimeException("Failed to read file: " + e.getMessage());
        }
    }

    public Map<String, Object> writeFile(String relativePath, String content) {
        Path p = baseWorkspace.resolve(relativePath).normalize();
        if (!p.startsWith(baseWorkspace)) {
            throw new IllegalArgumentException("Access denied: " + relativePath);
        }

        try {
            Files.createDirectories(p.getParent());
            Files.writeString(p, content != null ? content : "");
            return Map.of("success", true, "path", relativePath, "size", Files.size(p));
        } catch (IOException e) {
            throw new RuntimeException("Failed to write file: " + e.getMessage());
        }
    }

    public Map<String, Object> deleteFile(String relativePath) {
        Path p = baseWorkspace.resolve(relativePath).normalize();
        if (!p.startsWith(baseWorkspace) || !Files.exists(p)) {
            throw new IllegalArgumentException("File not found or access denied: " + relativePath);
        }

        try {
            Files.delete(p);
            return Map.of("success", true, "deleted", relativePath);
        } catch (IOException e) {
            throw new RuntimeException("Failed to delete file: " + e.getMessage());
        }
    }
}

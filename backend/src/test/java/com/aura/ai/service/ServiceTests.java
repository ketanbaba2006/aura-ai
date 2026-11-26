package com.aura.ai.service;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class ServiceTests {

    @Autowired
    private AuthService authService;

    @Autowired
    private ConversationService conversationService;

    @Autowired
    private ProjectService projectService;

    @Autowired
    private ToolService toolService;

    @Autowired
    private MonitoringService monitoringService;

    @Test
    void testAuthOperations() {
        // Test login / signup
        Map<String, Object> loginRes = authService.login("developer@aura.ai", "developer123");
        assertTrue((Boolean) loginRes.get("success"));
        assertNotNull(loginRes.get("access_token"));
        assertNotNull(loginRes.get("user"));

        // Test /me
        Map<String, Object> meRes = authService.getCurrentUser("developer@aura.ai");
        assertTrue((Boolean) meRes.get("success"));
        assertNotNull(meRes.get("user"));
    }

    @Test
    void testConversationOperations() {
        // Create conversation
        Map<String, Object> conv = conversationService.createConversation("Test Chat", "user_test");
        assertNotNull(conv.get("id"));
        String convId = (String) conv.get("id");

        // Save messages
        conversationService.saveMessage(convId, "user", "Hello AURA!", null, null);
        conversationService.saveMessage(convId, "assistant", "Hello! How can I help you?", null, null);

        // Get conversation with messages
        Map<String, Object> detail = conversationService.getConversation(convId);
        assertEquals("Test Chat", detail.get("title"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> msgs = (List<Map<String, Object>>) detail.get("messages");
        assertEquals(2, msgs.size());
    }

    @Test
    void testProjectOperations() {
        // List projects
        List<Map<String, Object>> projects = projectService.listProjects();
        assertFalse(projects.isEmpty());

        // Create project
        Map<String, Object> created = projectService.createProject("Test Project", "Desc", null, "web", "Dark", "Build app");
        assertNotNull(created.get("id"));
        assertEquals("Test Project", created.get("name"));
    }

    @Test
    void testToolOperations() {
        // Calculator
        Map<String, Object> calcRes = toolService.executeTool("calculator", Map.of("expression", "25 * 4 + 10"));
        assertEquals("success", calcRes.get("status"));
        assertEquals(110.0, ((Number) calcRes.get("result")).doubleValue());

        // System info
        Map<String, Object> sysRes = toolService.executeTool("system_info", Map.of());
        assertEquals("success", sysRes.get("status"));
        assertNotNull(sysRes.get("result"));
    }

    @Test
    void testMonitoringOperations() {
        Map<String, Object> metrics = monitoringService.getSystemMetrics();
        assertEquals("healthy", metrics.get("status"));
        assertNotNull(metrics.get("memory_used_mb"));
        assertNotNull(metrics.get("cpu_percent"));
    }
}

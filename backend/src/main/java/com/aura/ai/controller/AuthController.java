package com.aura.ai.controller;

import com.aura.ai.service.AuthService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/signup")
    public ResponseEntity<Map<String, Object>> signup(@RequestBody Map<String, String> body) {
        String name = body.getOrDefault("name", "Ketan Baba");
        String email = body.getOrDefault("email", "developer@aura.ai");
        String password = body.getOrDefault("password", "password123");

        Map<String, Object> response = authService.signup(name, email, password);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> body) {
        String email = body.getOrDefault("email", "developer@aura.ai");
        String password = body.getOrDefault("password", "password123");

        Map<String, Object> response = authService.login(email, password);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<Map<String, Object>> refresh(@RequestBody(required = false) Map<String, String> body,
                                                       @CookieValue(name = "refresh_token", required = false) String cookieRefreshToken) {
        String token = (body != null && body.containsKey("refresh_token"))
                ? body.get("refresh_token")
                : cookieRefreshToken;

        if (token == null || token.isBlank()) {
            return ResponseEntity.status(401).body(Map.of("success", false, "detail", "Refresh token missing"));
        }

        Map<String, Object> response = authService.refreshToken(token);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> getCurrentUser(Authentication authentication) {
        String emailOrId = authentication != null ? authentication.getName() : null;
        Map<String, Object> response = authService.getCurrentUser(emailOrId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout() {
        return ResponseEntity.ok(Map.of("success", true, "message", "Logged out successfully"));
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<Map<String, Object>> forgotPassword(@RequestBody Map<String, String> body) {
        String email = body.getOrDefault("email", "");
        Map<String, Object> response = authService.forgotPassword(email);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/reset-password")
    public ResponseEntity<Map<String, Object>> resetPassword(@RequestBody Map<String, String> body) {
        String token = body.getOrDefault("token", "");
        String password = body.getOrDefault("password", "");
        Map<String, Object> response = authService.resetPassword(token, password);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/verify-email")
    public ResponseEntity<Map<String, Object>> verifyEmail(@RequestParam("token") String token) {
        Map<String, Object> response = authService.verifyEmail(token);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/oauth/callback")
    public ResponseEntity<Map<String, Object>> oauthCallback(@RequestBody Map<String, String> body) {
        String provider = body.getOrDefault("provider", "google");
        String email = body.getOrDefault("email", "developer@aura.ai");
        String name = body.getOrDefault("name", "Ketan Baba");
        String avatarUrl = body.get("avatar_url");

        Map<String, Object> response = authService.oauthLogin(provider, email, name, avatarUrl);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/sessions")
    public ResponseEntity<Map<String, Object>> getSessions(Authentication authentication) {
        String userId = authentication != null ? authentication.getName() : "dev_user_001";
        return ResponseEntity.ok(Map.of("success", true, "sessions", authService.fetchSessions(userId)));
    }

    @PostMapping("/sessions/logout-all")
    public ResponseEntity<Map<String, Object>> logoutAll() {
        return ResponseEntity.ok(Map.of("success", true, "message", "All active sessions cleared"));
    }
}

package com.aura.ai.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

@Component
public class JwtTokenProvider {

    @Value("${aura.jwt.secret:aurasecretkey12345678901234567890123456789012}")
    private String jwtSecret;

    @Value("${aura.jwt.refresh-secret:71e87924e6ab471b2e7dede4fc8a5ca77e9cba6ce85fbea5d7c87278f4b4ce62}")
    private String refreshSecret;

    @Value("${aura.jwt.expiration-ms:86400000}")
    private long jwtExpirationMs;

    private SecretKey getSigningKey(String secret) {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            byte[] padded = new byte[32];
            System.arraycopy(keyBytes, 0, padded, 0, keyBytes.length);
            return Keys.hmacShaKeyFor(padded);
        }
        return Keys.hmacShaKeyFor(keyBytes);
    }

    public String generateAccessToken(String username, String userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", userId);
        claims.put("type", "access");

        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + jwtExpirationMs);

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(username)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(jwtSecret), SignatureAlgorithm.HS256)
                .compact();
    }

    public String generateRefreshToken(String username, String userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", userId);
        claims.put("type", "refresh");

        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + (7L * 24 * 3600 * 1000)); // 7 days

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(username)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(refreshSecret.isBlank() ? jwtSecret : refreshSecret), SignatureAlgorithm.HS256)
                .compact();
    }

    public String getUsernameFromToken(String token) {
        try {
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(getSigningKey(jwtSecret))
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            return claims.getSubject();
        } catch (Exception e) {
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(getSigningKey(refreshSecret.isBlank() ? jwtSecret : refreshSecret))
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            return claims.getSubject();
        }
    }

    public String getUserIdFromToken(String token) {
        try {
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(getSigningKey(jwtSecret))
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            return (String) claims.get("user_id");
        } catch (Exception e) {
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(getSigningKey(refreshSecret.isBlank() ? jwtSecret : refreshSecret))
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            return (String) claims.get("user_id");
        }
    }

    public boolean validateToken(String token) {
        if (token == null || token.isBlank()) return false;
        try {
            Jwts.parserBuilder().setSigningKey(getSigningKey(jwtSecret)).build().parseClaimsJws(token);
            return true;
        } catch (Exception ex) {
            try {
                Jwts.parserBuilder().setSigningKey(getSigningKey(refreshSecret.isBlank() ? jwtSecret : refreshSecret)).build().parseClaimsJws(token);
                return true;
            } catch (Exception e2) {
                return false;
            }
        }
    }
}

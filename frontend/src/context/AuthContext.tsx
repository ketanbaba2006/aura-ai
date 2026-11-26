/**
 * AURA OS Auth Context Provider
 * Handles login, signup, session tracking, token refreshing, and account guards.
 */

"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User, AuthSession } from "@/types";

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  loading: boolean;
  isOnline: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string }>;
  signup: (name: string, email: string, password: string) => Promise<{ success: boolean; message?: string; verification_token?: string }>;
  logout: () => Promise<void>;
  logoutAllDevices: () => Promise<void>;
  forgotPassword: (email: string) => Promise<{ success: boolean; message: string; reset_token?: string }>;
  resetPassword: (token: string, password: string) => Promise<{ success: boolean; message: string }>;
  verifyEmail: (token: string) => Promise<{ success: boolean; message: string }>;
  oauthLogin: (provider: "google" | "github", email: string, name: string, avatarUrl?: string) => Promise<{ success: boolean }>;
  fetchSessions: () => Promise<AuthSession[]>;
  setOnlineState: (online: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(true);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  // Check health and verify session on load
  const verifySession = useCallback(async () => {
    console.log("[AURA AUTH] verifySession starting...");
    try {
      const localToken = localStorage.getItem("aura_access_token");
      console.log("[AURA AUTH] localToken found in localStorage:", localToken ? `${localToken.substring(0, 15)}...` : "null");
      if (localToken) {
        console.log("[AURA AUTH] Fetching /auth/me with Bearer token");
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        let resp;
        try {
          resp = await fetch(`${apiBase}/auth/me`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${localToken}`
            },
            signal: controller.signal
          });
        } finally {
          clearTimeout(timeoutId);
        }
        console.log("[AURA AUTH] /auth/me response status:", resp.status);
        if (resp.ok) {
          const data = await resp.json();
          console.log("[AURA AUTH] /auth/me response data success:", data.success);
          if (data.success) {
            setAccessToken(localToken);
            setUser(data.user);
            setLoading(false);
            console.log("[AURA AUTH] Session successfully verified for user:", data.user.email);
            return;
          }
        } else {
          console.warn("[AURA AUTH] /auth/me returned non-ok status:", resp.status);
        }
      }

      console.log("[AURA AUTH] /auth/me failed or no localToken. Attempting silent refresh...");
      const refreshController = new AbortController();
      const refreshTimeoutId = setTimeout(() => refreshController.abort(), 5000);
      
      let resp;
      try {
        resp = await fetch(`${apiBase}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          signal: refreshController.signal
        });
      } finally {
        clearTimeout(refreshTimeoutId);
      }
      
      console.log("[AURA AUTH] /auth/refresh response status:", resp.status);
      if (resp.ok) {
        const data = await resp.json();
        console.log("[AURA AUTH] /auth/refresh response success:", data.success);
        if (data.success) {
          setAccessToken(data.access_token);
          setUser(data.user);
          localStorage.setItem("aura_access_token", data.access_token);
          console.log("[AURA AUTH] Session refreshed successfully:", data.user.email);
        } else {
          console.log("[AURA AUTH] /auth/refresh success was false. Cleared tokens.");
          localStorage.removeItem("aura_access_token");
          localStorage.removeItem("aura_csrf_token");
        }
      } else {
        console.log("[AURA AUTH] /auth/refresh request failed. Cleared tokens.");
        localStorage.removeItem("aura_access_token");
        localStorage.removeItem("aura_csrf_token");
      }
    } catch (err) {
      console.warn("[AURA AUTH] Session verification error:", err);
    } finally {
      setLoading(false);
      console.log("[AURA AUTH] verifySession finished. loading set to false.");
    }
  }, [apiBase]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get("token");
      const csrfParam = params.get("csrf");
      console.log("[AURA AUTH] useEffect mounted. URL search params present:", tokenParam ? "yes" : "no");
      
      if (tokenParam && csrfParam) {
        console.log("[AURA AUTH] Storing token and csrf to localStorage from URL");
        localStorage.setItem("aura_access_token", tokenParam);
        localStorage.setItem("aura_csrf_token", csrfParam);
        
        // Clean URL to keep it pretty and secure
        const cleanUrl = window.location.pathname + window.location.hash;
        console.log("[AURA AUTH] Cleaning URL to:", cleanUrl);
        window.history.replaceState({}, document.title, cleanUrl || "/");
      }
    }
    verifySession();
  }, [verifySession]);

  useEffect(() => {
    const handleLogoutEvent = () => {
      console.log("[AURA AUTH] handleLogoutEvent triggered. Resetting auth state.");
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("aura_access_token");
      localStorage.removeItem("aura_csrf_token");
    };
    window.addEventListener("aura-logout", handleLogoutEvent);
    return () => {
      window.removeEventListener("aura-logout", handleLogoutEvent);
    };
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      let resp;
      try {
        resp = await fetch(`${apiBase}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
          credentials: "include",
          signal: controller.signal
        });
      } finally {
        clearTimeout(timeoutId);
      }

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      if (data.success) {
        setAccessToken(data.access_token);
        setUser(data.user);
        
        // Save token to localStorage for fetch interceptors
        localStorage.setItem("aura_access_token", data.access_token);
        if (data.csrf_token) {
          localStorage.setItem("aura_csrf_token", data.csrf_token);
        }
        
        return { success: true };
      }
      return { success: false, message: "Login failed." };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  };

  const signup = async (name: string, email: string, password: string) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      let resp;
      try {
        resp = await fetch(`${apiBase}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
          signal: controller.signal
        });
      } finally {
        clearTimeout(timeoutId);
      }

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Signup failed.");
      }

      return { 
        success: true, 
        message: data.message,
        verification_token: data.verification_token
      };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  };

  const logout = async () => {
    try {
      await fetch(`${apiBase}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include"
      });
    } catch (err) {
      console.warn("Logout request failed:", err);
    } finally {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("aura_access_token");
      localStorage.removeItem("aura_csrf_token");
    }
  };

  const logoutAllDevices = async () => {
    try {
      const token = accessToken || localStorage.getItem("aura_access_token");
      await fetch(`${apiBase}/auth/sessions/logout-all`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        credentials: "include"
      });
    } catch (err) {
      console.warn("Logout all devices failed:", err);
    } finally {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("aura_access_token");
      localStorage.removeItem("aura_csrf_token");
    }
  };

  const forgotPassword = async (email: string) => {
    try {
      const resp = await fetch(`${apiBase}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Failed to initiate password reset.");
      }

      return { 
        success: true, 
        message: data.message,
        reset_token: data.reset_token
      };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  };

  const resetPassword = async (token: string, password: string) => {
    try {
      const resp = await fetch(`${apiBase}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Failed to reset password.");
      }

      return { success: true, message: data.message };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  };

  const verifyEmail = async (token: string) => {
    try {
      const resp = await fetch(`${apiBase}/auth/verify-email?token=${token}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Verification failed.");
      }

      return { success: true, message: data.message };
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  };

  const oauthLogin = async (
    provider: "google" | "github", 
    email: string, 
    name: string, 
    avatarUrl?: string
  ) => {
    try {
      // Mock OAuth callback simulation
      const resp = await fetch(`${apiBase}/auth/oauth/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          email,
          name,
          avatar_url: avatarUrl,
          oauth_token: "mock-oauth-token-aura-os"
        }),
        credentials: "include",
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "OAuth login failed.");
      }

      if (data.success) {
        setAccessToken(data.access_token);
        setUser(data.user);
        
        localStorage.setItem("aura_access_token", data.access_token);
        if (data.csrf_token) {
          localStorage.setItem("aura_csrf_token", data.csrf_token);
        }
        
        return { success: true };
      }
      return { success: false };
    } catch (err: any) {
      console.warn("OAuth error:", err);
      return { success: false };
    }
  };

  const fetchSessions = async (): Promise<AuthSession[]> => {
    try {
      const token = accessToken || localStorage.getItem("aura_access_token");
      const resp = await fetch(`${apiBase}/auth/sessions`, {
        method: "GET",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
      });

      const data = await resp.json();
      if (resp.ok && data.success) {
        return data.sessions;
      }
      return [];
    } catch (err) {
      console.warn("Failed to load sessions:", err);
      return [];
    }
  };

  const setOnlineState = useCallback((online: boolean) => {
    setIsOnline(online);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        loading,
        isOnline,
        login,
        signup,
        logout,
        logoutAllDevices,
        forgotPassword,
        resetPassword,
        verifyEmail,
        oauthLogin,
        fetchSessions,
        setOnlineState
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

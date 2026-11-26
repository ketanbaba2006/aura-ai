



/**
 * AURA OS Holographic Login Screen
 * Futuristic glassmorphic auth panel with neon glows and smooth transitions.
 */

"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useNotification } from "@/context/NotificationContext";
import { AuraAvatar } from "@/components/chat/AuraAvatar";
import { Mail, Lock, User as UserIcon, ArrowRight, KeyRound } from "lucide-react";

export function LoginScreen() {
  const { login, signup, forgotPassword, resetPassword, oauthLogin } = useAuth();
  const { showToast } = useNotification();

  const [mode, setMode] = useState<"login" | "signup" | "forgot" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [loading, setLoading] = useState(false);


  // Development convenience helper
  const [devTokenInfo, setDevTokenInfo] = useState<string | null>(null);

  // Check for OAuth redirect errors in URL parameters
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const errorParam = params.get("error");
      if (errorParam) {
        let msg = "OAuth authentication failed.";
        if (errorParam === "google_auth_denied") {
          msg = "Google login access was denied or cancelled.";
        } else if (errorParam === "google_exchange_failed") {
          msg = "Failed to exchange Google code. Backend configuration may be incorrect.";
        } else if (errorParam === "missing_email") {
          msg = "Google profile does not contain an email address.";
        } else if (errorParam === "account_deactivated") {
          msg = "This administrator account is currently deactivated.";
        }
        showToast(msg, "error");

        // Clear query parameters from URL to avoid re-triggering toast on reload
        const cleanUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, document.title, cleanUrl || "/");
      }
    }
  }, [showToast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setLoading(true);
    setDevTokenInfo(null);

    try {
      if (mode === "login") {
        const res = await login(email, password);
        if (res.success) {
          showToast("Authentication successful. Welcome to AURA OS.", "success");
        } else {
          showToast(res.message || "Invalid credentials", "error");
        }
      } else if (mode === "signup") {
        if (!name || !password) return;
        const res = await signup(name, email, password);
        if (res.success) {
          showToast("Account initialized. Email verification token generated in logs.", "success");
          if (res.verification_token) {
            setDevTokenInfo(`[DEV BYPASS] Verification Token: ${res.verification_token}. Use link: /verify-email?token=${res.verification_token}`);
          }
          setMode("login");
        } else {
          showToast(res.message || "Signup failed", "error");
        }
      } else if (mode === "forgot") {
        const res = await forgotPassword(email);
        if (res.success) {
          showToast("Recovery token generated. Checked terminal/logs.", "success");
          if (res.reset_token) {
            setDevTokenInfo(`[DEV BYPASS] Reset Token: ${res.reset_token}. Go to: http://localhost:3000/reset-password?token=${res.reset_token}`);
          }
        } else {
          showToast(res.message || "Failed to submit recovery", "error");
        }
      } else if (mode === "reset") {
        if (!resetToken || !password) return;
        const res = await resetPassword(resetToken, password);
        if (res.success) {
          showToast("Password updated successfully. Please sign in.", "success");
          setMode("login");
        } else {
          showToast(res.message || "Failed to reset password", "error");
        }
      }
    } catch (err: any) {
      showToast(err.message || "An unexpected error occurred", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setLoading(true);

    if (provider === "google") {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      window.location.href = `${apiBase}/auth/google/login`;
      return;
    }

    // Simulate standard OAuth callback
    const mockEmail = `${provider}_user_${Math.floor(Math.random() * 1000)}@aura.os`;
    const mockName = `${provider.toUpperCase()} Core Dev`;
    const mockAvatar = provider === "github" 
      ? "https://github.com/github.png" 
      : "https://lh3.googleusercontent.com/a/default-user";

    try {
      const res = await oauthLogin(provider, mockEmail, mockName, mockAvatar);
      if (res.success) {
        showToast(`Authenticated via ${provider.toUpperCase()} successfully.`, "success");
      } else {
        showToast(`OAuth authentication failed for ${provider}`, "error");
      }
    } catch (err) {
      showToast("OAuth flow error", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "100vw",
        height: "100vh",
        background: "radial-gradient(circle at 50% 50%, #07070d 0%, #020204 100%)",
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        padding: "20px"
      }}
    >
      {/* Moving grid overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(6, 214, 214, 0.005) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 214, 214, 0.005) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
          maskImage: "radial-gradient(circle, black, transparent 80%)",
          WebkitMaskImage: "radial-gradient(circle, black, transparent 80%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          background: "rgba(10, 10, 20, 0.65)",
          backdropFilter: "blur(24px)",
          border: "1px solid rgba(255, 255, 255, 0.04)",
          borderRadius: "24px",
          padding: "32px",
          boxShadow: "0 24px 64px -12px rgba(0, 0, 0, 0.8), var(--glow-cyan)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Holographic header */}
        <div style={{ marginBottom: "24px", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <AuraAvatar size={80} state={loading ? "thinking" : "idle"} />
          <h1
            className="holo-text"
            style={{
              fontSize: "20px",
              fontWeight: "800",
              marginTop: "16px",
              letterSpacing: "3px",
              textTransform: "uppercase"
            }}
          >
            AURA AI
          </h1>
          <p style={{ fontSize: "11px", color: "rgba(168, 255, 0, 0.4)", letterSpacing: "2px", marginTop: "4px", textTransform: "uppercase" }}>
            Alien-Tech Authentication
          </p>
        </div>

        {/* Dynamic Form container */}
        <form onSubmit={handleSubmit} style={{ width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}>
          
            {mode === "signup" && (
              <div
                key="signup-name"
                style={{ overflow: "hidden" }}
              >
                <div style={{ position: "relative" }}>
                  <span style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
                    <UserIcon size={16} />
                  </span>
                  <input
                    type="text"
                    placeholder="Terminal Administrator Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "12px 16px 12px 42px",
                      background: "rgba(0, 0, 0, 0.3)",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                      borderRadius: "12px",
                      color: "var(--text-primary)",
                      fontSize: "13.5px",
                      outline: "none",
                      transition: "border-color 0.25s, box-shadow 0.25s",
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = "var(--accent-cyan)";
                      e.target.style.boxShadow = "var(--glow-cyan)";
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = "rgba(255, 255, 255, 0.05)";
                      e.target.style.boxShadow = "none";
                    }}
                  />
                </div>
              </div>
            )}

            {mode === "reset" && (
              <div
                key="reset-token"
                style={{ overflow: "hidden" }}
              >
                <div style={{ position: "relative" }}>
                  <span style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
                    <KeyRound size={16} />
                  </span>
                  <input
                    type="text"
                    placeholder="Reset Authorization Token"
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "12px 16px 12px 42px",
                      background: "rgba(0, 0, 0, 0.3)",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                      borderRadius: "12px",
                      color: "var(--text-primary)",
                      fontSize: "13.5px",
                      outline: "none",
                    }}
                  />
                </div>
              </div>
            )}
          

          {/* Email field (hidden in reset password mode) */}
          {mode !== "reset" && (
            <div style={{ position: "relative" }}>
              <span style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
                <Mail size={16} />
              </span>
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "12px 16px 12px 42px",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  borderRadius: "12px",
                  color: "var(--text-primary)",
                  fontSize: "13.5px",
                  outline: "none",
                  transition: "border-color 0.25s, box-shadow 0.25s",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "var(--accent-cyan)";
                  e.target.style.boxShadow = "var(--glow-cyan)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.05)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>
          )}

          {/* Password field (hidden in forgot password mode) */}
          {mode !== "forgot" && (
            <div style={{ position: "relative" }}>
              <span style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
                <Lock size={16} />
              </span>
              <input
                type="password"
                placeholder={mode === "signup" ? "Create Password" : mode === "reset" ? "Create New Password" : "Password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "12px 16px 12px 42px",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  borderRadius: "12px",
                  color: "var(--text-primary)",
                  fontSize: "13.5px",
                  outline: "none",
                  transition: "border-color 0.25s, box-shadow 0.25s",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "var(--accent-cyan)";
                  e.target.style.boxShadow = "var(--glow-cyan)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.05)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>
          )}

          {/* Forgot password trigger link */}
          {mode === "login" && (
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => setMode("forgot")}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-secondary)",
                  fontSize: "11px",
                  cursor: "pointer",
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = "var(--accent-cyan)"}
                onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-secondary)"}
              >
                Restore terminal access?
              </button>
            </div>
          )}

          {/* Main Action Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: "12px",
              background: "var(--accent-gradient)",
              color: "var(--bg-primary)",
              border: "none",
              fontWeight: "700",
              fontSize: "14px",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: "var(--glow-cyan-strong)",
              opacity: loading ? 0.7 : 1,
            }}
          >
            <span>
              {mode === "login" 
                ? "Initiate Access" 
                : mode === "signup" 
                ? "Initialize Workspace" 
                : mode === "forgot" 
                ? "Request Key" 
                : "Reset Credentials"}
            </span>
            <ArrowRight size={14} />
          </button>
        </form>

        {/* Developer Token Bypass Tool */}
        {devTokenInfo && (
          <div style={{
            width: "100%",
            marginTop: "16px",
            padding: "10px",
            borderRadius: "8px",
            background: "rgba(6, 214, 214, 0.05)",
            border: "1px solid rgba(6, 214, 214, 0.15)",
            fontSize: "10px",
            color: "var(--accent-cyan)",
            wordBreak: "break-all",
            fontFamily: "monospace",
            textAlign: "center"
          }}>
            {devTokenInfo}
          </div>
        )}

        {/* Separator */}
        {(mode === "login" || mode === "signup") && (
          <div style={{ display: "flex", alignItems: "center", width: "100%", margin: "20px 0" }}>
            <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.04)" }} />
            <span style={{ padding: "0 10px", fontSize: "10px", color: "var(--text-muted)", letterSpacing: "1px", textTransform: "uppercase" }}>
              Secure Providers
            </span>
            <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.04)" }} />
          </div>
        )}

        {/* OAuth Buttons */}
        {(mode === "login" || mode === "signup") && (
          <div style={{ display: "flex", gap: "10px", width: "100%" }}>
            <button
              onClick={() => handleOAuth("google")}
              style={{
                flex: 1,
                padding: "10px",
                borderRadius: "10px",
                background: "rgba(255, 255, 255, 0.01)",
                border: "1px solid rgba(255, 255, 255, 0.04)",
                color: "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: "500",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                cursor: "pointer",
                transition: "all var(--transition-fast)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(6, 214, 214, 0.03)";
                e.currentTarget.style.borderColor = "rgba(6, 214, 214, 0.2)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.01)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.04)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.113-5.136 4.113-3.48 0-6.3-2.82-6.3-6.3 0-3.48 2.82-6.3 6.3-6.3 1.63 0 3.106.623 4.22 1.64l3.13-3.13C19.23 2.67 15.93 1.2 12.24 1.2c-6.07 0-11 4.93-11 11s4.93 11 11 11c6.33 0 10.53-4.45 10.53-10.74 0-.72-.08-1.27-.23-1.875H12.24z"/>
              </svg>
              <span>Google</span>
            </button>
            <button
              onClick={() => handleOAuth("github")}
              style={{
                flex: 1,
                padding: "10px",
                borderRadius: "10px",
                background: "rgba(255, 255, 255, 0.01)",
                border: "1px solid rgba(255, 255, 255, 0.04)",
                color: "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: "500",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                cursor: "pointer",
                transition: "all var(--transition-fast)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(139, 92, 246, 0.03)";
                e.currentTarget.style.borderColor = "rgba(139, 92, 246, 0.2)";
                e.currentTarget.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.01)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.04)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.137 20.162 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
              </svg>
              <span>GitHub</span>
            </button>
          </div>
        )}

        {/* Mode Toggles */}
        <div style={{ marginTop: "24px", fontSize: "12px", color: "var(--text-secondary)" }}>
          {mode === "login" && (
            <span>
              New administrator?{" "}
              <button
                onClick={() => { setMode("signup"); setDevTokenInfo(null); }}
                style={{ background: "none", border: "none", color: "var(--accent-cyan)", fontWeight: "600", cursor: "pointer" }}
              >
                Initialize Terminal
              </button>
            </span>
          )}
          {mode === "signup" && (
            <span>
              Registered administrator?{" "}
              <button
                onClick={() => { setMode("login"); setDevTokenInfo(null); }}
                style={{ background: "none", border: "none", color: "var(--accent-cyan)", fontWeight: "600", cursor: "pointer" }}
              >
                Access Terminal
              </button>
            </span>
          )}
          {mode === "forgot" && (
            <span>
              Remembered access?{" "}
              <button
                onClick={() => { setMode("login"); setDevTokenInfo(null); }}
                style={{ background: "none", border: "none", color: "var(--accent-cyan)", fontWeight: "600", cursor: "pointer" }}
              >
                Go back
              </button>
              {" / "}
              <button
                onClick={() => { setMode("reset"); setDevTokenInfo(null); }}
                style={{ background: "none", border: "none", color: "var(--accent-purple)", fontWeight: "600", cursor: "pointer" }}
              >
                Enter token
              </button>
            </span>
          )}
          {mode === "reset" && (
            <span>
              Abort recovery?{" "}
              <button
                onClick={() => { setMode("login"); setDevTokenInfo(null); }}
                style={{ background: "none", border: "none", color: "var(--accent-cyan)", fontWeight: "600", cursor: "pointer" }}
              >
                Cancel
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

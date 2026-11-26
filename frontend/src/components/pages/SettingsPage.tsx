/**
 * AURA OS Settings Dashboard Page
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

interface SystemHealth {
  status: string;
  version: string;
  active_provider: string;
  active_model: string;
  latency: string;
  quota_status: string;
  failover_chain: string;
  requests_today: number;
  tools_loaded: number;
  search_cache: number;
}

export function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(true);
  const [purging, setPurging] = useState(false);
  const [webSearchMode, setWebSearchMode] = useState("ask_first");
  const [developerMode, setDeveloperMode] = useState(false);
  const [monitorStats, setMonitorStats] = useState<any>(null);
  
  // ── Deep Research Settings states ──
  const [researchProvider, setResearchProvider] = useState("bedrock");
  const [researchApiKey, setResearchApiKey] = useState("");
  const [researchModel, setResearchModel] = useState("anthropic.claude-3-5-sonnet-20241022-v2:0");
  const [researchAwsRegion, setResearchAwsRegion] = useState("us-east-1");
  const [researchTemperature, setResearchTemperature] = useState("0.3");
  const [researchDepth, setResearchDepth] = useState("standard");
  const [researchSourcesLimit, setResearchSourcesLimit] = useState("8");
  const [researchTimeout, setResearchTimeout] = useState("300");

  const { showToast, showModal } = useNotification();
  const passwordRef = useRef("");

  const fetchHealth = useCallback(async () => {
    setIsLoadingHealth(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/health`);
      if (resp.ok) {
        const data = await resp.json();
        setHealth(data);
      }
    } catch (e) {
      console.error("Failed to load health stats", e);
    } finally {
      setIsLoadingHealth(false);
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/settings`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.web_search_mode) {
          setWebSearchMode(data.web_search_mode);
        }
      }

      const rResp = await fetchWithAuth(`${apiBase}/research/settings`);
      if (rResp.ok) {
        const rData = await rResp.json();
        if (rData.research_provider) setResearchProvider(rData.research_provider);
        if (rData.research_api_key) setResearchApiKey(rData.research_api_key);
        if (rData.research_model) setResearchModel(rData.research_model);
        if (rData.research_aws_region) setResearchAwsRegion(rData.research_aws_region);
        if (rData.research_temperature) setResearchTemperature(rData.research_temperature);
        if (rData.research_depth) setResearchDepth(rData.research_depth);
        if (rData.research_sources_limit) setResearchSourcesLimit(rData.research_sources_limit);
        if (rData.research_timeout) setResearchTimeout(rData.research_timeout);
      }
    } catch (e) {
      console.error("Failed to fetch settings", e);
    }
  }, []);

  const fetchMonitorStats = useCallback(async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_developer_token") || "";
      const resp = await fetchWithAuth(`${apiBase}/monitoring/stats`, {
        headers: {
          "X-Developer-Token": token
        }
      });
      if (resp.ok) {
        const data = await resp.json();
        setMonitorStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch monitoring stats", e);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    fetchSettings();
    const devModeStored = localStorage.getItem("aura_developer_mode") === "true";
    setDeveloperMode(devModeStored);
  }, [fetchHealth, fetchSettings]);

  useEffect(() => {
    if (developerMode) {
      fetchMonitorStats();
      const interval = setInterval(fetchMonitorStats, 3000);
      return () => clearInterval(interval);
    }
  }, [developerMode, fetchMonitorStats]);

  const executeAuth = async (password: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/monitoring/auth`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password })
      });
      if (resp.ok) {
        const data = await resp.json();
        localStorage.setItem("aura_developer_token", data.token);
        localStorage.setItem("aura_developer_mode", "true");
        setDeveloperMode(true);
        showToast("Developer Mode enabled. Live LLM telemetry active.", "success");
        fetchMonitorStats();
      } else {
        showToast("Authentication failed: Incorrect password.", "error");
        setDeveloperMode(false);
        localStorage.setItem("aura_developer_mode", "false");
        localStorage.removeItem("aura_developer_token");
      }
    } catch (e) {
      showToast("Failed to authenticate with backend service.", "error");
    }
  };

  const promptDeveloperAuth = () => {
    passwordRef.current = "";
    showModal({
      title: "🔐 Developer Mode Authentication",
      description: "Entering Developer Mode exposes internal folders, system logs, and LLM telemetry. Enter developer password to authenticate.",
      content: (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "500" }}>Password</span>
          <input
            type="password"
            placeholder="Enter password..."
            onChange={(e) => {
              passwordRef.current = e.target.value;
            }}
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              background: "var(--bg-tertiary)",
              color: "var(--text)",
              border: "1px solid var(--border)",
              fontSize: "14px",
              outline: "none",
              width: "100%"
            }}
            autoFocus
          />
        </div>
      ),
      actions: [
        {
          label: "Authenticate",
          variant: "primary",
          onClick: () => {
            executeAuth(passwordRef.current);
          }
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const handleDevModeToggle = (checked: boolean) => {
    if (checked) {
      promptDeveloperAuth();
    } else {
      setDeveloperMode(false);
      localStorage.setItem("aura_developer_mode", "false");
      localStorage.removeItem("aura_developer_token");
      showToast("Developer Mode disabled.", "info");
    }
  };

  const handleWebSearchModeChange = async (val: string) => {
    setWebSearchMode(val);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/settings/web_search_mode`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: val })
      });
      if (!resp.ok) {
        throw new Error("Failed to update setting");
      }
      showToast("Web search settings updated successfully.", "success");
    } catch (e) {
      showToast("Failed to update web search mode settings.", "error");
    }
  };

  const handleUpdateResearchSetting = async (key: string, value: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/research/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value })
      });
      if (resp.ok) {
        showToast(`Research setting ${key.replace("research_", "")} updated.`, "success");
      } else {
        const err = await resp.json();
        showToast(`Failed to update setting: ${err.detail || "Error"}`, "error");
      }
    } catch (e) {
      showToast("Error updating research settings.", "error");
    }
  };

  const handleClearCache = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/search/cache`, { method: "DELETE" });
      if (resp.ok) {
        showToast("Web search cache successfully purged!", "success");
        fetchHealth();
      }
    } catch (e) {
      showToast("Failed to clear search cache.", "error");
    }
  };

  const handleSystemWipe = () => {
    showModal({
      title: "Confirm System Wipe",
      description: "CRITICAL WARNING: This will completely wipe all conversations, indexed documents, planning tasks, and activity logs. Are you absolutely sure?",
      actions: [
        {
          label: "Wipe System",
          variant: "danger",
          onClick: executeSystemWipe
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const executeSystemWipe = async () => {
    setPurging(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      
      // Clear logs
      await fetchWithAuth(`${apiBase}/logs`, { method: "DELETE" });
      
      // Clear cache
      await fetchWithAuth(`${apiBase}/search/cache`, { method: "DELETE" });
      
      // Fetch conversations to delete each
      const convResp = await fetchWithAuth(`${apiBase}/conversations`);
      if (convResp.ok) {
        const conversations = await convResp.json();
        for (const c of conversations) {
          await fetchWithAuth(`${apiBase}/conversations/${c.id}`, { method: "DELETE" });
        }
      }

      // Fetch docs to delete each
      const docResp = await fetchWithAuth(`${apiBase}/knowledge/documents`);
      if (docResp.ok) {
        const docs = await docResp.json();
        for (const d of docs) {
          await fetchWithAuth(`${apiBase}/knowledge/documents/${d.id}`, { method: "DELETE" });
        }
      }

      // Fetch goals to delete each
      const goalResp = await fetchWithAuth(`${apiBase}/planner/goals`);
      if (goalResp.ok) {
        const goals = await goalResp.json();
        for (const g of goals) {
          await fetchWithAuth(`${apiBase}/planner/goals/${g.id}`, { method: "DELETE" });
        }
      }

      showToast("System wiped successfully. All databases reinitialized.", "success");
      fetchHealth();
    } catch (e) {
      showToast("Error wiping system database.", "error");
    } finally {
      setPurging(false);
    }
  };

  return (
    <div 
      className="page-container"
      style={{ padding: "40px", height: "100%", overflowY: "auto" }}
    >
      <div className="page-header" style={{ marginBottom: "32px" }}>
        <h1 style={{ 
          fontSize: "32px", 
          fontWeight: "800", 
          color: "var(--text)", 
          marginBottom: "8px",
          textShadow: "0 0 40px rgba(6, 214, 214, 0.3)"
        }}>
          ⚙️ Settings & System Metrics
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "15px" }}>
          System details, health status, and maintenance triggers for AURA OS.
        </p>
      </div>

      <div 
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "28px" }}
      >
        {/* Web Search Control Card */}
        <div 
          className="chat-card"
          style={{ 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.05), rgba(139, 92, 246, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)", 
            display: "flex", 
            flexDirection: "column", 
            gap: "16px",
            backdropFilter: "blur(12px)",
            transformStyle: "preserve-3d"
          }}
        >
          <div>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "6px", fontWeight: "700" }}>Web Search Control</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Configure how AURA routes queries that might need real-time web search.
            </p>
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
            <label style={{ fontSize: "14px", color: "var(--text-secondary)", fontWeight: "600" }}>Web Search Mode</label>
            <select
              value={webSearchMode}
              onChange={(e) => handleWebSearchModeChange(e.target.value)}
              style={{
                padding: "12px 16px",
                borderRadius: "10px",
                background: "var(--bg-tertiary)",
                color: "var(--text)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                fontSize: "14px",
                outline: "none",
                cursor: "pointer",
                width: "100%",
                backdropFilter: "blur(8px)"
              }}
            >
              <option value="ask_first">Ask First (Default)</option>
              <option value="automatic">Automatic</option>
              <option value="never">Never</option>
            </select>
          </div>
        </div>

        {/* Deep Research Provider Settings Card */}
        <div 
          className="chat-card"
          style={{ 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(6, 214, 214, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)", 
            display: "flex", 
            flexDirection: "column", 
            gap: "16px",
            backdropFilter: "blur(12px)",
            transformStyle: "preserve-3d"
          }}
        >
          <div>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "6px", fontWeight: "700" }}>🔬 Deep Research Settings</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Configure the isolated provider and parameters for Deep Research reports.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>Provider</label>
              <select
                value={researchProvider}
                onChange={(e) => {
                  setResearchProvider(e.target.value);
                  handleUpdateResearchSetting("research_provider", e.target.value);
                }}
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-tertiary)",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "13px",
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                <option value="bedrock">AWS Bedrock</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="openrouter">OpenRouter</option>
                <option value="perplexity">Perplexity AI</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>Model</label>
              <input
                type="text"
                value={researchModel}
                onChange={(e) => setResearchModel(e.target.value)}
                onBlur={(e) => handleUpdateResearchSetting("research_model", e.target.value)}
                placeholder="e.g. anthropic.claude-3-5-sonnet..."
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-tertiary)",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>API Key</label>
            <input
              type="password"
              value={researchApiKey}
              onChange={(e) => setResearchApiKey(e.target.value)}
              onBlur={(e) => handleUpdateResearchSetting("research_api_key", e.target.value)}
              placeholder="Paste research provider API Key..."
              style={{
                padding: "10px 14px",
                borderRadius: "8px",
                background: "var(--bg-tertiary)",
                color: "var(--text)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                fontSize: "13px",
                outline: "none",
              }}
            />
          </div>

          {researchProvider === "bedrock" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>AWS Region</label>
              <input
                type="text"
                value={researchAwsRegion}
                onChange={(e) => setResearchAwsRegion(e.target.value)}
                onBlur={(e) => handleUpdateResearchSetting("research_aws_region", e.target.value)}
                placeholder="us-east-1"
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-tertiary)",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>Sources Limit</label>
              <input
                type="number"
                value={researchSourcesLimit}
                onChange={(e) => setResearchSourcesLimit(e.target.value)}
                onBlur={(e) => handleUpdateResearchSetting("research_sources_limit", e.target.value)}
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-tertiary)",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>Timeout (secs)</label>
              <input
                type="number"
                value={researchTimeout}
                onChange={(e) => setResearchTimeout(e.target.value)}
                onBlur={(e) => handleUpdateResearchSetting("research_timeout", e.target.value)}
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-tertiary)",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>Temperature</label>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "600" }}>{researchTemperature}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.5"
              step="0.1"
              value={researchTemperature}
              onChange={(e) => setResearchTemperature(e.target.value)}
              onMouseUp={() => handleUpdateResearchSetting("research_temperature", researchTemperature)}
              onTouchEnd={() => handleUpdateResearchSetting("research_temperature", researchTemperature)}
              style={{
                width: "100%",
                accentColor: "var(--primary)",
                cursor: "pointer",
              }}
            />
          </div>
        </div>

        {/* Developer Mode Switch Card */}
        <div 
          className="chat-card"
          style={{ 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.05), rgba(139, 92, 246, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)", 
            display: "flex", 
            flexDirection: "column", 
            gap: "16px",
            backdropFilter: "blur(12px)",
            transformStyle: "preserve-3d"
          }}
        >
          <div>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "6px", fontWeight: "700" }}>Developer Mode</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Toggle live LLM routing monitor to view telemetry, active provider queue logs and system statistics.
            </p>
          </div>
          
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "12px", background: "var(--bg-tertiary)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
            <span style={{ fontSize: "14px", color: "var(--text)", fontWeight: "600" }}>Enable Live Monitor</span>
            <button
              onClick={() => handleDevModeToggle(!developerMode)}
              style={{
                padding: "10px 20px",
                borderRadius: "8px",
                background: developerMode 
                  ? "linear-gradient(135deg, rgba(6, 214, 214, 0.3), rgba(139, 92, 246, 0.3))" 
                  : "rgba(255, 255, 255, 0.05)",
                color: developerMode ? "#000" : "var(--text)",
                border: "1px solid " + (developerMode ? "var(--primary)" : "rgba(255, 255, 255, 0.1)"),
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: "700",
                boxShadow: developerMode ? "0 0 20px rgba(6, 214, 214, 0.3)" : "none"
              }}
            >
              {developerMode ? "ACTIVE" : "INACTIVE"}
            </button>
          </div>
        </div>

        {/* Environment Status Card */}
        <div 
          className="chat-card"
          style={{ 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.05), rgba(139, 92, 246, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)",
            backdropFilter: "blur(12px)",
            transformStyle: "preserve-3d"
          }}
        >
          <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px", fontWeight: "700" }}>Environmental Status</h2>

          {isLoadingHealth ? (
            <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Fetching health metrics...</div>
          ) : !health ? (
            <div style={{ color: "var(--error)", fontSize: "14px" }}>AURA is offline. Ensure local service is running.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Developer & Owner</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700" }}>Ketan Lade</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>AURA Version</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700" }}>{health.version}</span>
              </div>
              
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Current Provider</span>
                <span style={{
                  fontSize: "14px",
                  fontWeight: "800",
                  color: health.active_provider === "GROQ" ? "#34d399" :
                         health.active_provider === "GEMINI" ? "#60a5fa" :
                         health.active_provider === "OPENROUTER" ? "#a78bfa" : "#fb923c",
                  textTransform: "uppercase"
                }}>
                  {health.active_provider}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Current Model</span>
                <span style={{ color: "var(--primary)", fontSize: "14px", fontWeight: "700", fontFamily: "monospace" }}>{health.active_model}</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Provider Status</span>
                <span style={{
                  fontSize: "14px",
                  fontWeight: "700",
                  color: health.quota_status.includes("Healthy") ? "#34d399" :
                         health.quota_status.includes("Unconfigured") ? "var(--text-muted)" : "#f87171"
                }}>
                  {health.quota_status}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Latency</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700", fontFamily: "monospace" }}>{health.latency}</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Requests Today</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700" }}>{health.requests_today} requests</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Failover Chain</span>
                <span 
                  style={{ color: "var(--text-secondary)", fontSize: "12px", fontWeight: "700", fontFamily: "monospace", display: "flex", flexWrap: "wrap", gap: "4px" }}
                  dangerouslySetInnerHTML={{ __html: health.failover_chain }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "10px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Loaded Tools (Plugins)</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700" }}>{health.tools_loaded} tools</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", paddingBottom: "6px" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "14px", fontWeight: "500" }}>Cached Search Pages</span>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "700" }}>{health.search_cache} pages</span>
              </div>
            </div>
          )}
        </div>

        {/* System Operations Card */}
        <div 
          className="chat-card"
          style={{ 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(239, 68, 68, 0.05), rgba(251, 146, 60, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)", 
            borderTop: "4px solid rgba(239, 68, 68, 0.5)", 
            display: "flex", 
            flexDirection: "column", 
            gap: "20px",
            backdropFilter: "blur(12px)",
            transformStyle: "preserve-3d"
          }}
        >
          <div>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "6px", fontWeight: "700" }}>System Operations</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Administrative actions and database garbage collectors.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div
              style={{ 
                display: "flex", 
                justifyContent: "space-between", 
                alignItems: "center", 
                background: "rgba(255,255,255,0.02)", 
                padding: "16px", 
                borderRadius: "10px", 
                border: "1px solid rgba(255, 255, 255, 0.1)" 
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "600" }}>Purge Search Cache</span>
                <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Deletes Playwright scraped page caches.</span>
              </div>
              <button
                onClick={handleClearCache}
                style={{
                  padding: "10px 20px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, rgba(6, 214, 214, 0.15), rgba(139, 92, 246, 0.15))",
                  color: "var(--text)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600"
                }}
              >
                Clear Cache
              </button>
            </div>

            <div
              style={{ 
                display: "flex", 
                justifyContent: "space-between", 
                alignItems: "center", 
                background: "rgba(239, 68, 68, 0.05)", 
                padding: "16px", 
                borderRadius: "10px", 
                border: "1px solid rgba(239, 68, 68, 0.2)" 
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "600" }}>Factory Reset Databases</span>
                <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Purges SQLite & Vector DBs entirely.</span>
              </div>
              <button
                onClick={handleSystemWipe}
                disabled={purging}
                style={{
                  padding: "10px 20px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(248, 113, 113, 0.2))",
                  color: "#f87171",
                  border: "1px solid rgba(239, 68, 68, 0.4)",
                  cursor: "pointer",
                  fontWeight: "700",
                  fontSize: "13px",
                  boxShadow: "0 0 20px rgba(239, 68, 68, 0.2)"
                }}
              >
                {purging ? "Wiping..." : "Reset System"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {developerMode && (
        <div 
          className="chat-card"
          style={{ 
            marginTop: "28px", 
            padding: "24px", 
            borderRadius: "16px", 
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.05), rgba(139, 92, 246, 0.05))", 
            border: "1px solid rgba(255, 255, 255, 0.1)", 
            display: "flex", 
            flexDirection: "column", 
            gap: "20px",
            backdropFilter: "blur(12px)"
          }}
        >
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <h2 style={{ fontSize: "18px", color: "var(--text)", fontWeight: "700" }}>📊 Live LLM Routing Monitor</h2>
              <span
                style={{ 
                  fontSize: "12px", 
                  background: "rgba(52, 211, 153, 0.15)", 
                  color: "#34d399", 
                  padding: "6px 12px", 
                  borderRadius: "999px", 
                  fontWeight: "700",
                  border: "1px solid rgba(52, 211, 153, 0.3)"
                }}
              >
                Telemetry Active
              </span>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Real-time priority queues routing, latency logs, and automated failover records.
            </p>
          </div>

          {!monitorStats ? (
            <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Connecting to telemetry stream...</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* Telemetry Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "20px" }}>
                {/* Active Provider Card */}
                <div
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "18px", 
                    borderRadius: "12px", 
                    border: "1px solid rgba(255, 255, 255, 0.1)", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "8px" 
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "1px" }}>Current Provider</span>
                  <span style={{
                    fontSize: "20px",
                    fontWeight: "800",
                    color: monitorStats.active_provider === "groq" ? "#34d399" :
                           monitorStats.active_provider === "gemini" ? "#60a5fa" :
                           monitorStats.active_provider === "openrouter" ? "#a78bfa" : "#fb923c",
                    textTransform: "uppercase"
                  }}>
                    {monitorStats.active_provider}
                  </span>
                </div>

                {/* Current Model Card */}
                <div
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "18px", 
                    borderRadius: "12px", 
                    border: "1px solid rgba(255, 255, 255, 0.1)", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "8px" 
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "1px" }}>Current Model</span>
                  <span style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={monitorStats.circuits?.[monitorStats.active_provider]?.model || "unknown"}>
                    {monitorStats.circuits?.[monitorStats.active_provider]?.model || "unknown"}
                  </span>
                </div>

                {/* Requests Tally Card */}
                <div
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "18px", 
                    borderRadius: "12px", 
                    border: "1px solid rgba(255, 255, 255, 0.1)", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "8px" 
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "1px" }}>Total Queries</span>
                  <span style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)" }}>
                    {monitorStats.requests}
                  </span>
                </div>

                {/* Fallbacks Card */}
                <div
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "18px", 
                    borderRadius: "12px", 
                    border: "1px solid rgba(255, 255, 255, 0.1)", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "8px" 
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "1px" }}>Failures / Fallbacks</span>
                  <span style={{ fontSize: "20px", fontWeight: "800", color: monitorStats.failures > 0 ? "#f87171" : "var(--text)" }}>
                    {monitorStats.failures}
                  </span>
                </div>

                {/* Cache Hits Card */}
                <div
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "18px", 
                    borderRadius: "12px", 
                    border: "1px solid rgba(255, 255, 255, 0.1)", 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "8px" 
                  }}
                >
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "1px" }}>Cache Hits</span>
                  <span style={{ fontSize: "20px", fontWeight: "800", color: "#34d399" }}>
                    {monitorStats.cache_hits}
                  </span>
                </div>
              </div>

              {/* AI Provider Status Dashboard */}
              <div>
                <h3 style={{ fontSize: "14px", color: "var(--text)", marginBottom: "12px", fontWeight: "700" }}>AI Provider Status Dashboard</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
                  {["gemini", "groq", "openrouter"].map((provider, index) => {
                    const status = monitorStats.status[provider] || "active";
                    const latency = monitorStats.avg_latencies[provider] || 0.0;
                    
                    // Circuit details from backend
                    const circuit = monitorStats.circuits?.[provider] || { state: "CLOSED", consecutive_failures: 0, quota_exhausted: false, cooldown_remaining: 0, remaining_requests: 100, model: "unknown" };
                    
                    // Determine Online/Offline status
                    const isOnline = status === "active";
                    const isUnconfigured = status === "unconfigured";
                    const isQuotaExceeded = status === "quota_exhausted" || circuit.quota_exhausted;
                    
                    let circuitStateText = "Circuit Closed (Healthy)";
                    let circuitColor = "#34d399"; // Green
                    
                    if (isUnconfigured) {
                      circuitStateText = "API Key Missing";
                      circuitColor = "var(--text-muted)";
                    } else if (isQuotaExceeded) {
                      circuitStateText = "Quota Exhausted (429)";
                      circuitColor = "#fb923c"; // Orange
                    } else if (circuit.state === "OPEN") {
                      circuitStateText = `Circuit Open (Cooldown: ${circuit.cooldown_remaining}s)`;
                      circuitColor = "#f87171"; // Red
                    } else if (circuit.state === "HALF_OPEN") {
                      circuitStateText = "Circuit Half-Open (Testing)";
                      circuitColor = "#facc15"; // Yellow
                    } else if (status === "error") {
                      circuitStateText = "Connection Degraded";
                      circuitColor = "#f87171";
                    }

                    return (
                      <div 
                        key={provider}
                        style={{ 
                          background: "var(--bg-tertiary)", 
                          padding: "18px", 
                          borderRadius: "12px", 
                          border: "1px solid rgba(255, 255, 255, 0.1)", 
                          display: "flex", 
                          flexDirection: "column",
                          gap: "12px",
                          position: "relative",
                          overflow: "hidden",
                          transformStyle: "preserve-3d"
                        }}
                      >
                        {/* Glow indicator line */}
                        <div style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          right: 0,
                          height: "4px",
                          background: isUnconfigured ? "transparent" : isOnline ? "linear-gradient(90deg, #34d399, transparent)" : "linear-gradient(90deg, #f87171, transparent)"
                        }} />

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: "14px", fontWeight: "800", textTransform: "uppercase", color: "var(--text-primary)", letterSpacing: "0.5px" }}>{provider}</span>
                          
                          {/* Online/Offline Badge */}
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div
                              style={{
                                width: "10px",
                                height: "10px",
                                borderRadius: "50%",
                                background: isUnconfigured ? "var(--text-muted)" : isOnline ? "#34d399" : "#f87171",
                                boxShadow: isUnconfigured ? "none" : isOnline ? "0 0 10px #34d399" : "0 0 10px #f87171"
                              }} 
                            />
                            <span style={{ 
                              fontSize: "11px", 
                              fontWeight: "700", 
                              color: isUnconfigured ? "var(--text-muted)" : isOnline ? "#34d399" : "#f87171",
                              textTransform: "uppercase" 
                            }}>
                              {isUnconfigured ? "OFFLINE" : isOnline ? "ONLINE" : "OFFLINE"}
                            </span>
                          </div>
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "700" }}>CIRCUIT STATE</span>
                          <span style={{ fontSize: "12px", color: circuitColor, fontWeight: "700" }}>{circuitStateText}</span>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255, 255, 255, 0.05)", paddingTop: "10px", marginTop: "4px" }}>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600" }}>RESPONSE LATENCY</span>
                          <span style={{ fontSize: "12px", fontWeight: "800", fontFamily: "monospace", color: isUnconfigured ? "var(--text-muted)" : "#34d399" }}>
                            {isUnconfigured || latency === 0.0 ? "N/A" : `${latency.toFixed(2)}s`}
                          </span>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255, 255, 255, 0.05)", paddingTop: "10px" }}>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600" }}>REMAINING REQUESTS</span>
                          <span style={{ fontSize: "12px", fontWeight: "800", fontFamily: "monospace", color: isUnconfigured ? "var(--text-muted)" : "#60a5fa" }}>
                            {isUnconfigured ? "N/A" : circuit.remaining_requests}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Fallback Console Logs */}
              <div>
                <h3 style={{ fontSize: "14px", color: "var(--text)", marginBottom: "12px", fontWeight: "700" }}>Telemetry Event Console</h3>
                <div style={{
                  background: "rgba(0, 0, 0, 0.4)",
                  padding: "18px",
                  borderRadius: "12px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontFamily: "monospace",
                  fontSize: "12px",
                  maxHeight: "180px",
                  overflowY: "auto",
                  color: "#e2e8f0",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px"
                }}>
                  {monitorStats.fallback_events.length === 0 ? (
                    <span style={{ color: "var(--text-muted)" }}>[CONSOLE] No fallback events recorded. System routing running optimally.</span>
                  ) : (
                    monitorStats.fallback_events.map((evt: any, i: number) => (
                      <div key={i} style={{ lineHeight: "1.6" }}>
                        <span style={{ color: "#a78bfa" }}>[{evt.timestamp}]</span>{" "}
                        <span style={{ color: "#f87171", fontWeight: "700" }}>FAIL: {evt.failed_provider}</span>{" "}
                        <span style={{ color: "#94a3b8" }}>&rarr;</span>{" "}
                        <span style={{ color: "#60a5fa", fontWeight: "700" }}>ROUTE: {evt.fallback_to}</span>{" "}
                        <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>({evt.error})</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

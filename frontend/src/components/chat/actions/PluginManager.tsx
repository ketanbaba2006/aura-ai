"use client";

import { useEffect, useState } from "react";
import { Puzzle, X, Check, Power, RefreshCw, HelpCircle } from "lucide-react";
import { fetchTools } from "@/lib/api";
import type { ToolInfo } from "@/types";

interface PluginManagerProps {
  onClose: () => void;
}

export function PluginManager({ onClose }: PluginManagerProps) {
  const [plugins, setPlugins] = useState<ToolInfo[]>([]);
  const [enabledPlugins, setEnabledPlugins] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPlugins = async () => {
    setLoading(true);
    setError(null);
    try {
      const toolList = await fetchTools();
      setPlugins(toolList);
      
      // Load toggles from localStorage
      const cached = localStorage.getItem("aura_enabled_plugins");
      if (cached) {
        setEnabledPlugins(JSON.parse(cached));
      } else {
        // Default all to enabled
        const initial: Record<string, boolean> = {};
        toolList.forEach((tool) => {
          initial[tool.name] = true;
        });
        setEnabledPlugins(initial);
        localStorage.setItem("aura_enabled_plugins", JSON.stringify(initial));
      }
    } catch (err) {
      console.warn("Failed to load tools from backend:", err);
      // Fallback local list of tools
      const fallbackTools: ToolInfo[] = [
        { name: "web_search", description: "Query Google/Chromium engine for live, real-time facts.", parameters: {} },
        { name: "code_runner", description: "Execute Python/JS operations inside isolated sandbox environments.", parameters: {} },
        { name: "calculator", description: "Solve complex algebraic expressions with absolute mathematical precision.", parameters: {} },
        { name: "knowledge_retrieval", description: "Query indexed PDF, text, and markdown files stored in vector storage.", parameters: {} },
        { name: "system_info", description: "Retrieve host specs, disk metrics, CPU telemetry, and runtime data.", parameters: {} },
      ];
      setPlugins(fallbackTools);
      const cached = localStorage.getItem("aura_enabled_plugins");
      if (cached) {
        setEnabledPlugins(JSON.parse(cached));
      } else {
        const initial: Record<string, boolean> = {};
        fallbackTools.forEach((t) => {
          initial[t.name] = true;
        });
        setEnabledPlugins(initial);
        localStorage.setItem("aura_enabled_plugins", JSON.stringify(initial));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlugins();
  }, []);

  const togglePlugin = (name: string) => {
    const updated = {
      ...enabledPlugins,
      [name]: !enabledPlugins[name],
    };
    setEnabledPlugins(updated);
    localStorage.setItem("aura_enabled_plugins", JSON.stringify(updated));
  };

  const getToolIcon = (name: string) => {
    switch (name) {
      case "web_search":
        return "🌍";
      case "code_runner":
        return "💻";
      case "calculator":
        return "📊";
      case "knowledge_retrieval":
        return "🧠";
      case "system_info":
        return "⚙️";
      default:
        return "🔌";
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "380px",
        background: "#05050a",
        borderRadius: "14px",
        overflow: "hidden",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        position: "relative",
      }}
    >
      {/* Header */}
      <div
        style={{
          width: "100%",
          padding: "12px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)",
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: "12px", fontWeight: "600", color: "#fff", display: "flex", alignItems: "center", gap: "6px" }}>
          <Puzzle size={14} style={{ color: "var(--accent-cyan)" }} />
          PLUGIN CONTROL CENTER
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={loadPlugins}
            style={{
              background: "none",
              border: "none",
              color: "rgba(255,255,255,0.6)",
              cursor: "pointer",
            }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "rgba(255,255,255,0.6)",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Plugins List */}
      <div
        style={{
          flex: 1,
          width: "100%",
          padding: "20px 16px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {loading ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", color: "var(--text-muted)" }}>
            Loading plugin configuration...
          </div>
        ) : plugins.length === 0 ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", color: "var(--text-muted)" }}>
            No tools or plugins discovered.
          </div>
        ) : (
          plugins.map((plugin) => {
            const isEnabled = !!enabledPlugins[plugin.name];
            return (
              <div
                key={plugin.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 12px",
                  borderRadius: "10px",
                  background: isEnabled ? "rgba(6, 214, 214, 0.02)" : "rgba(255, 255, 255, 0.01)",
                  border: isEnabled ? "1px solid rgba(6, 214, 214, 0.08)" : "1px solid rgba(255, 255, 255, 0.03)",
                  transition: "all var(--transition-fast)",
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", flex: 1, marginRight: "12px" }}>
                  <div style={{ fontSize: "18px", padding: "6px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "6px" }}>
                    {getToolIcon(plugin.name)}
                  </div>
                  <div>
                    <h4 style={{ fontSize: "12.5px", fontWeight: "600", color: "#fff", textTransform: "capitalize" }}>
                      {plugin.name.replace(/_/g, " ")}
                    </h4>
                    <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px", lineHeight: "1.4" }}>
                      {plugin.description}
                    </p>
                  </div>
                </div>

                {/* Cyber Switch Control */}
                <button
                  onClick={() => togglePlugin(plugin.name)}
                  style={{
                    width: "44px",
                    height: "22px",
                    borderRadius: "999px",
                    backgroundColor: isEnabled ? "rgba(6, 214, 214, 0.2)" : "rgba(255,255,255,0.05)",
                    border: isEnabled ? "1px solid rgba(6, 214, 214, 0.4)" : "1px solid rgba(255,255,255,0.1)",
                    position: "relative",
                    cursor: "pointer",
                    padding: 0,
                    transition: "all 0.2s ease",
                    outline: "none",
                  }}
                >
                  <div
                    style={{
                      width: "16px",
                      height: "16px",
                      borderRadius: "50%",
                      backgroundColor: isEnabled ? "var(--accent-cyan)" : "var(--text-muted)",
                      position: "absolute",
                      top: "2px",
                      left: isEnabled ? "24px" : "3px",
                      transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                      boxShadow: isEnabled ? "0 0 8px var(--accent-cyan)" : "none",
                    }}
                  />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer info */}
      <div
        style={{
          width: "100%",
          padding: "12px 16px",
          background: "rgba(10, 10, 18, 0.95)",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <HelpCircle size={12} style={{ color: "var(--text-muted)" }} />
        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
          Disabled plugins will not be queried or routed during automated Agent loops.
        </span>
      </div>
    </div>
  );
}

/**
 * AURA AI Status Badge
 * Shows intelligent status during response generation:
 * Analyzing, Reasoning, Searching Knowledge, Connecting Concepts, Building Response
 * Also displays the active model when idle.
 */

"use client";

import { useEffect, useState } from "react";
import type { ToolUsage } from "@/types";

interface StatusBadgeProps {
  isStreaming: boolean;
  toolUsages: ToolUsage[];
  searchStatus: string | null;
  activeModel?: { provider: string; model: string; fallback?: boolean } | null;
}

const THINKING_STATES = [
  "Analyzing query",
  "Reasoning",
  "Connecting concepts",
  "Building response",
];

function getStatusText(
  isStreaming: boolean,
  toolUsages: ToolUsage[],
  searchStatus: string | null,
  thinkingIdx: number
): string | null {
  if (!isStreaming) return null;

  // Check active tools
  const activeTool = toolUsages.find((t) => t.isLoading);
  if (activeTool) {
    switch (activeTool.name) {
      case "web_search":
        return "Searching the web";
      case "knowledge_retrieval":
        return "Searching knowledge base";
      case "calculator":
        return "Computing";
      case "code_runner":
        return "Executing code";
      case "system_info":
        return "Reading system info";
      default:
        return `Using ${activeTool.name}`;
    }
  }

  if (searchStatus) return searchStatus;

  // Cycle through thinking states
  return THINKING_STATES[thinkingIdx % THINKING_STATES.length];
}

function getProviderColor(provider: string): string {
  switch (provider.toLowerCase()) {
    case "groq": return "#34d399"; // green
    case "gemini": return "#60a5fa"; // blue
    case "openrouter": return "#a78bfa"; // purple
    case "bedrock": return "#fb923c"; // orange
    case "openai": return "#22c55e"; // green
    case "anthropic": return "#f97316"; // orange
    case "perplexity": return "#06b6d4"; // cyan
    default: return "var(--text-secondary)";
  }
}

export function StatusBadge({ isStreaming, toolUsages, searchStatus, activeModel }: StatusBadgeProps) {
  const [thinkingIdx, setThinkingIdx] = useState(0);

  useEffect(() => {
    if (!isStreaming) {
      setThinkingIdx(0);
      return;
    }

    const interval = setInterval(() => {
      setThinkingIdx((prev) => prev + 1);
    }, 2500);

    return () => clearInterval(interval);
  }, [isStreaming]);

  const statusText = getStatusText(isStreaming, toolUsages, searchStatus, thinkingIdx);

  return (
    <>
      {statusText && (
        <div
          key={statusText}
          className="ai-status-badge"
          style={{ 
            transformStyle: "preserve-3d",
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.15), rgba(139, 92, 246, 0.15))",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "999px",
            padding: "6px 12px",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <span className="status-icon" />
          <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-primary)" }}>{statusText}</span>
        </div>
      )}
      {!isStreaming && activeModel && (
        <div
          className="model-status-badge"
          style={{
            transformStyle: "preserve-3d",
            background: "linear-gradient(135deg, rgba(6, 214, 214, 0.1), rgba(139, 92, 246, 0.1))",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "999px",
            padding: "4px 10px",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "11px",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: getProviderColor(activeModel.provider),
              boxShadow: `0 0 8px ${getProviderColor(activeModel.provider)}`,
            }}
          />
          <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
            {activeModel.provider.toUpperCase()}
          </span>
          <span style={{ color: "var(--text-muted)", fontWeight: "500" }}>
            {activeModel.fallback ? "↻ " : ""}{activeModel.model}
          </span>
        </div>
      )}
    </>
  );
}

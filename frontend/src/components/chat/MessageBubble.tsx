/**
 * AURA AI Message Bubble
 * Individual message display with markdown, tool usage, and search results.
 */

"use client";

import { useState, useEffect } from "react";
import type { AgentProgress, Message, ToolUsage } from "@/types";
import { Copy, RotateCcw, Check, BookOpen, Terminal, Search, Code, Sparkles, User, Circle, LoaderCircle, X, FileText, ChevronDown, ChevronUp, Clock, Compass, ShieldAlert, AlertCircle } from "lucide-react";
import { useNotification } from "@/context/NotificationContext";
import { motion } from "framer-motion";
import { ArtifactViewer } from "@/components/artifacts/ArtifactViewer";
import { AuraAvatar } from "./AuraAvatar";
import { AgentExecutionTracker } from "../agent/AgentExecutionTracker";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
  toolUsages?: ToolUsage[];
  searchStatus?: string | null;
  agentProgress?: AgentProgress[];
  onOpenArtifact?: (title: string, content: string, language?: string) => void;
  onSendHint?: (hint: string) => void;
  onRegenerate?: (messageId: string) => void;
  activeView?: string;
  isGenerating?: boolean;
}

export function MessageBubble({ 
  message, 
  toolUsages, 
  searchStatus, 
  agentProgress, 
  onOpenArtifact, 
  onSendHint,
  onRegenerate,
  activeView,
  isGenerating = false
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const { showToast } = useNotification();

  const researchReport = message.metadata?.research_report as {
    id: string;
    topic: string;
    markdown: string;
    pdf: string;
    docx: string;
  } | undefined;

  const handleDownloadReport = async (filePath: string, fileName: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_access_token") || "";
      const url = `${apiBase}/research/download?path=${encodeURIComponent(filePath)}`;
      
      const resp = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      
      if (!resp.ok) {
        throw new Error("Download failed");
      }
      
      const blob = await resp.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      showToast("Download started successfully", "success");
    } catch (err) {
      console.error(err);
      showToast("Download failed. File may be unavailable.", "error");
    }
  };

  if (isSystem) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`message ${message.role}`}
      style={{
        display: "flex",
        gap: "12px",
        flexDirection: isUser ? "row-reverse" : "row",
        alignItems: "flex-start",
        marginBottom: "24px",
        width: "100%",
      }}
    >
      {/* Avatar */}
      {!isUser && (
      <div 
        className="message-avatar"
        style={{
          width: "34px",
          height: "34px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          background: "transparent",
        }}
      >
        <AuraAvatar size={30} state={isGenerating ? "generating" : "idle"} />
      </div>
      )}

      {/* Content wrapper */}
      <div className="message-content" style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%", maxWidth: message.metadata?.search_metrics ? "900px" : "85%", margin: message.metadata?.search_metrics ? "0 auto" : undefined }}>
        {activeView !== "chat" && agentProgress && agentProgress.length > 0 && (
          <AgentProgressCard progress={agentProgress} />
        )}

        {!!message.metadata?.search_metrics && (
          <DeepResearchProgressCard 
            metrics={message.metadata.search_metrics as SearchMetrics} 
            isCompleted={!!researchReport}
          />
        )}
        {/* Search status indicator */}
        {activeView !== "chat" && searchStatus && (
          <div className="search-status" style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 12px", background: "var(--surface-glass)", borderRadius: "12px", border: "1px solid var(--surface-border)", fontSize: "12px", color: "var(--text-primary)" }}>
            <Search size={12} className="animate-pulse" />
            <span>{searchStatus}</span>
          </div>
        )}

        {/* Tool Activity Timeline Group */}
        {activeView !== "chat" && toolUsages && toolUsages.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
            {toolUsages.map((tool, idx) => (
              <ToolActivityPill key={idx} tool={tool} />
            ))}
          </div>
        )}

          <div 
          className="message-bubble"
          style={{
            background: isUser ? "var(--bg-elevated)" : "transparent",
            border: "none",
            borderRadius: isUser ? "24px" : "0",
            padding: isUser ? "12px 20px" : "4px 0",
            fontSize: "16px",
            lineHeight: "1.7",
            wordBreak: "break-word",
            color: "var(--text-primary)",
            maxWidth: "100%",
          }}
        >
          {researchReport && (
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px", paddingBottom: "16px", borderBottom: "1px solid var(--surface-border)" }}>
              <button
                onClick={() => handleDownloadReport(researchReport.pdf, `${researchReport.topic}.pdf`)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "6px 12px",
                  background: "var(--surface-glass)",
                  border: "1px solid var(--surface-border)",
                  color: "var(--text-primary)",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: "500",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--surface-glass-hover)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "var(--surface-glass)"; }}
              >
                <FileText size={12} />
                <span>Export PDF</span>
              </button>
              <button
                onClick={() => handleDownloadReport(researchReport.docx, `${researchReport.topic}.docx`)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "6px 12px",
                  background: "var(--surface-glass)",
                  border: "1px solid var(--surface-border)",
                  color: "var(--text-primary)",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: "500",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "var(--surface-glass-hover)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "var(--surface-glass)"; }}
              >
                <BookOpen size={12} />
                <span>Export Word</span>
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(message.content);
                  showToast("Report copied to clipboard", "success");
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "6px 12px",
                  background: "transparent",
                  border: "1px solid transparent",
                  color: "var(--text-muted)",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: "500",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-primary)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}
              >
                <Copy size={12} />
                <span>Copy</span>
              </button>
            </div>
          )}
          {message.content ? (
            <div className={message.metadata?.search_metrics ? "deep-research-article" : "markdown-content"}>
              <MarkdownRenderer content={message.content} onOpenArtifact={onOpenArtifact} onSendHint={onSendHint} activeView={activeView} />
            </div>
          ) : message.isStreaming ? (
            <div className="typing-dots" style={{ display: "flex", gap: "4px", padding: "6px 0" }}>
              <div className="typing-dot" style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--text-muted)", animation: "bounce-dot 1.4s infinite ease-in-out both" }} />
              <div className="typing-dot" style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--text-muted)", animation: "bounce-dot 1.4s infinite ease-in-out both", animationDelay: "0.16s" }} />
              <div className="typing-dot" style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--text-muted)", animation: "bounce-dot 1.4s infinite ease-in-out both", animationDelay: "0.32s" }} />
            </div>
          ) : null}
          {message.isStreaming && message.content && (
            <span className="streaming-cursor" style={{ display: "inline-block", width: "2px", height: "15px", background: "var(--accent-cyan)", marginLeft: "4px", verticalAlign: "text-bottom", animation: "blink 0.8s infinite" }} />
          )}
        </div>



        {/* Message Actions */}
        {!isUser && message.content && (
          <div style={{ display: "flex", gap: "10px", marginTop: "6px", paddingLeft: "4px" }}>
            <button
              onClick={() => {
                navigator.clipboard.writeText(message.content);
                showToast("Copied to clipboard!", "success");
              }}
              style={{
                background: "var(--surface-glass)",
                border: "1px solid var(--surface-border)",
                color: "var(--text-muted)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "11px",
                padding: "6px 10px",
                borderRadius: "8px",
                transition: "all var(--transition-fast)",
                outline: "none"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--text-primary)";
                e.currentTarget.style.background = "var(--surface-glass-hover)";
                e.currentTarget.style.borderColor = "var(--surface-border-hover)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
                e.currentTarget.style.background = "var(--surface-glass)";
                e.currentTarget.style.borderColor = "var(--surface-border)";
              }}
              title="Copy message"
            >
              <Copy size={12} />
              <span>Copy</span>
            </button>
            <button
              onClick={() => onRegenerate && onRegenerate(message.id)}
              style={{
                background: "var(--surface-glass)",
                border: "1px solid var(--surface-border)",
                color: "var(--text-muted)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "11px",
                padding: "6px 10px",
                borderRadius: "8px",
                transition: "all var(--transition-fast)",
                outline: "none"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--text-primary)";
                e.currentTarget.style.background = "var(--surface-glass-hover)";
                e.currentTarget.style.borderColor = "var(--surface-border-hover)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
                e.currentTarget.style.background = "var(--surface-glass)";
                e.currentTarget.style.borderColor = "var(--surface-border)";
              }}
              title="Regenerate"
            >
              <RotateCcw size={12} />
              <span>Regenerate</span>
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function AgentProgressCard({ progress }: { progress: AgentProgress[] }) {
  const phases: AgentProgress["phase"][] = ["Planning", "Generating Code", "Testing", "Fixing Errors", "Deployment"];
  const byPhase = new Map(progress.map((item) => [item.phase, item]));

  const tasks = phases.map((phase, idx) => {
    const item = byPhase.get(phase);
    let detailStr = item?.detail || '';
    if (item?.tasks && item.tasks.length > 0) {
      detailStr += '\n' + item.tasks.map(t => `[${t.status === 'completed' ? 'x' : t.status === 'failed' ? '!' : ' '}] ${t.title}`).join('\n');
    }
    
    return {
      id: `phase-${idx}`,
      name: phase,
      status: (item?.status || 'pending') as 'pending' | 'running' | 'completed' | 'failed',
      detail: detailStr || undefined
    };
  });

  return (
    <div style={{ marginBottom: "16px", width: "100%", maxWidth: "600px" }}>
      <AgentExecutionTracker tasks={tasks} title="Autonomous Agent Progress" />
    </div>
  );
}

function ToolActivityPill({ tool }: { tool: ToolUsage }) {
  const [expanded, setExpanded] = useState(false);
  const isSource = tool.name === "web_search" || tool.name === "knowledge_retrieval";
  
  const icon = tool.name === "web_search" 
    ? <Search size={12} /> 
    : tool.name === "knowledge_retrieval"
    ? <BookOpen size={12} />
    : tool.name === "calculator"
    ? <Code size={12} />
    : <Terminal size={12} />;
    
  const label = isSource ? "Sources Used" : "Execution Details";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "6px", width: "100%" }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 12px",
          borderRadius: "14px",
          background: "rgba(255, 255, 255, 0.02)",
          color: "var(--text-secondary)",
          border: "1px solid rgba(255, 255, 255, 0.04)",
          fontSize: "12px",
          fontWeight: "500",
          cursor: "pointer",
          transition: "all var(--transition-fast)",
          outline: "none"
        }}
      >
        <span style={{ display: "flex", alignItems: "center", color: tool.success === false ? "var(--error)" : "var(--accent-cyan)" }}>
          {tool.isLoading ? <div className="tool-spinner" style={{ width: "10px", height: "10px", border: "1.5px solid rgba(6, 214, 214, 0.15)", borderTopColor: "var(--accent-cyan)" }} /> : icon}
        </span>
        <span style={{ fontSize: "11px", fontWeight: "600" }}>{label}</span>
        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
          {expanded ? "Hide Details ▴" : "Show Details ▾"}
        </span>
      </button>

      {expanded && tool.result && (
        <div style={{ width: "100%", paddingLeft: "8px", marginTop: "2px" }}>
          {tool.success === false ? (
            <div style={{ fontSize: "11px", color: "var(--error)", fontFamily: "monospace", background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.15)", borderRadius: "8px", padding: "8px 12px" }}>
              Error: {tool.result}
            </div>
          ) : (
            <ExpandableResult result={tool.result} isSearch={tool.name === "web_search"} />
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Expandable panel for long raw tool results
 */
function ExpandableResult({ result, isSearch }: { result: string; isSearch: boolean }) {
  const [expanded, setExpanded] = useState(false);

  if (isSearch) {
    return <SearchResultDisplay result={result} />;
  }

  const lines = result.split("\n");
  const isLong = result.length > 150 || lines.length > 3;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
      <pre 
        style={{
          margin: 0,
          background: "rgba(0, 0, 0, 0.35)",
          border: "1px solid rgba(255, 255, 255, 0.03)",
          borderRadius: "8px",
          padding: "10px 14px",
          width: "100%",
          maxHeight: expanded ? "400px" : "68px",
          overflow: expanded ? "auto" : "hidden",
          fontFamily: "monospace",
          fontSize: "11.5px",
          color: "var(--text-secondary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
          transition: "max-height 0.25s ease"
        }}
      >
        <code>{result}</code>
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: "none",
            border: "none",
            color: "var(--accent-cyan)",
            fontSize: "10px",
            cursor: "pointer",
            padding: 0,
            textDecoration: "underline",
            marginTop: "2px"
          }}
        >
          {expanded ? "Show less ▴" : "Expand output ▾"}
        </button>
      )}
    </div>
  );
}

/**
 * Displays web search results in a structured card format.
 */
function SearchResultDisplay({ result }: { result: string }) {
  const lines = result.split("\n");
  const sources: { url: string; title: string }[] = [];

  let inSources = false;
  for (const line of lines) {
    if (line.includes("━━━ Sources ━━━")) {
      inSources = true;
      continue;
    }
    if (inSources) {
      const match = line.match(/^\[(\d+)\]\s+(https?:\/\/.+)/);
      if (match) {
        sources.push({ url: match[2], title: `Source ${match[1]}` });
      }
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", width: "100%" }}>
      {sources.length > 0 && (
        <div style={{ display: "flex", flexWrap: "nowrap", gap: "10px", overflowX: "auto", paddingBottom: "4px" }}>
          {sources.map((src, i) => {
            const domain = new URL(src.url).hostname.replace("www.", "");
            return (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                title={src.title}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                  padding: "10px 12px",
                  background: "var(--surface-glass)",
                  border: "1px solid var(--surface-border)",
                  borderRadius: "12px",
                  minWidth: "140px",
                  maxWidth: "180px",
                  textDecoration: "none",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.06)";
                  e.currentTarget.style.borderColor = "rgba(6, 214, 214, 0.3)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "var(--surface-glass)";
                  e.currentTarget.style.borderColor = "var(--surface-border)";
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <Compass size={12} color="var(--accent-cyan)" />
                  <span style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    {domain}
                  </span>
                </div>
                <span style={{ fontSize: "12px", color: "var(--text-primary)", fontWeight: "500", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {src.title}
                </span>
              </a>
            );
          })}
        </div>
      )}
      
      <div style={{ maxHeight: "150px", overflow: "hidden", position: "relative", fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
        {result.substring(0, 500)}
        {result.length > 500 && "..."}
      </div>
    </div>
  );
}

function highlightCode(code: string, lang: string) {
  let escaped = code
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const placeholders: string[] = [];

  // Multi-line comments
  escaped = escaped.replace(/\/\*[\s\S]*?\*\//g, (match) => {
    placeholders.push(`<span class="code-comment">${match}</span>`);
    return `___PLACEHOLDER_${placeholders.length - 1}___`;
  });

  // Single-line comments
  escaped = escaped.replace(/(\/\/.*|#.*)/g, (match) => {
    placeholders.push(`<span class="code-comment">${match}</span>`);
    return `___PLACEHOLDER_${placeholders.length - 1}___`;
  });

  // Strings
  escaped = escaped.replace(/(["'`])([\s\S]*?)\1/g, (match) => {
    placeholders.push(`<span class="code-string">${match}</span>`);
    return `___PLACEHOLDER_${placeholders.length - 1}___`;
  });

  // Keywords
  const keywords = /\b(const|let|var|function|return|import|export|from|default|class|extends|if|else|for|while|try|catch|async|await|def|fn|print|console|log|public|private|protected|interface|type|implements|new|this|throw|switch|case|break|continue|null|undefined|true|false)\b/g;
  escaped = escaped.replace(keywords, '<span class="code-keyword">$1</span>');

  // Numbers
  escaped = escaped.replace(/\b(\d+)\b/g, '<span class="code-number">$1</span>');

  // Restore placeholders
  for (let i = placeholders.length - 1; i >= 0; i--) {
    escaped = escaped.replace(`___PLACEHOLDER_${i}___`, placeholders[i]);
  }

  return escaped;
}

function CodeBlock({
  code,
  lang,
  onOpenArtifact
}: {
  code: string;
  lang: string;
  onOpenArtifact?: (title: string, content: string, language?: string) => void;
}) {
  const { showToast } = useNotification();
  const lines = code.split("\n");

  let filename = `sandbox.${lang === "react" ? "jsx" : lang || "txt"}`;
  const firstLine = code.split("\n")[0].trim();
  const fileCommentMatch = firstLine.match(/^(?:#|\/\/|\/\*|<!--)\s*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)/);
  if (fileCommentMatch) {
    filename = fileCommentMatch[1];
  }

  return (
    <div className="static-code-block" style={{
      margin: "14px 0",
      borderRadius: "10px",
      border: "1px solid rgba(255, 255, 255, 0.04)",
      background: "#050508",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      display: "flex",
      flexDirection: "column",
      maxHeight: "400px",
      overflow: "hidden"
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 16px",
        background: "rgba(255, 255, 255, 0.02)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
        fontSize: "12px",
        color: "var(--text-secondary)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontFamily: "monospace", color: "var(--accent-cyan)", fontWeight: "600" }}>{filename}</span>
          <span style={{ fontSize: "10px", background: "rgba(255,255,255,0.05)", padding: "2px 6px", borderRadius: "4px", textTransform: "uppercase" }}>{lang}</span>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => {
              navigator.clipboard.writeText(code);
              showToast("Copied to clipboard!", "success");
            }}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "11px",
              padding: "2px 6px",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              outline: "none"
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = "var(--text-primary)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
          >
            Copy
          </button>
          {onOpenArtifact && (
            <button
              onClick={() => onOpenArtifact(filename, code, lang)}
              style={{
                background: "rgba(6, 214, 214, 0.08)",
                border: "1px solid rgba(6, 214, 214, 0.2)",
                color: "var(--accent-cyan)",
                padding: "2px 8px",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "11px",
                fontWeight: "600",
                outline: "none"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(6, 214, 214, 0.15)";
                e.currentTarget.style.boxShadow = "0 0 8px rgba(6, 214, 214, 0.2)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(6, 214, 214, 0.08)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              Run Sandbox
            </button>
          )}
        </div>
      </div>
      {/* Code Area */}
      <div style={{
        flex: 1,
        overflow: "auto",
        display: "flex",
        padding: "12px 0",
        fontFamily: "monospace",
        fontSize: "12.5px",
        lineHeight: "1.6",
        background: "#030305"
      }}>
        {/* Line Numbers */}
        <div style={{
          padding: "0 12px 0 16px",
          color: "rgba(255, 255, 255, 0.12)",
          textAlign: "right",
          userSelect: "none",
          borderRight: "1px solid rgba(255, 255, 255, 0.02)",
          flexShrink: 0
        }}>
          {lines.map((_, idx) => (
            <div key={idx}>{idx + 1}</div>
          ))}
        </div>
        {/* Code Content */}
        <pre style={{
          margin: 0,
          padding: "0 16px",
          overflow: "visible",
          color: "#cbd5e1",
          whiteSpace: "pre",
          flex: 1
        }}>
          <code dangerouslySetInnerHTML={{ __html: highlightCode(code, lang) }} />
        </pre>
      </div>
    </div>
  );
}

function MarkdownRenderer({
  content,
  onOpenArtifact,
  onSendHint,
  activeView
}: {
  content: string;
  onOpenArtifact?: (title: string, content: string, language?: string) => void;
  onSendHint?: (hint: string) => void;
  activeView?: string;
}) {
  return (
    <div className="markdown-body" style={{ color: "var(--text-primary)", fontSize: "14px", lineHeight: "1.7" }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const lang = match ? match[1] : '';
            const codeString = String(children).replace(/\n$/, '');
            
            if (!inline && lang === 'aura-artifact') {
              try {
                const artifact = JSON.parse(codeString);
                const name = artifact.name || artifact.slug || "";
                const isInternal = name.includes("test") || name.includes("retry") || name.includes("log") || name.includes("tmp") || name.includes("debug");
                
                if (activeView !== "chat" && !isInternal) {
                  return (
                    <ArtifactViewer 
                      artifact={artifact} 
                      onOpenWorkspace={onOpenArtifact ? () => onOpenArtifact(name, "View Project in Workspace", "project") : undefined} 
                    />
                  );
                }
              } catch (e) {
                if (activeView !== "chat") {
                  return <CodeBlock code={codeString} lang="json" />;
                }
              }
              return null;
            } else if (!inline) {
              return (
                <CodeBlock code={codeString} lang={lang} onOpenArtifact={onOpenArtifact} />
              );
            }
            return <code className={className} style={{ background: 'var(--bg-tertiary)', padding: '3px 6px', borderRadius: '6px', fontSize: '13px', color: 'var(--text-primary)' }} {...props}>{children}</code>;
          },
          table({ children, ...props }) {
            return (
              <div style={{ overflowX: "auto", margin: "16px 0", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.08)" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }} {...props}>
                  {children}
                </table>
              </div>
            );
          },
          thead({ children, ...props }) {
            return <thead style={{ background: "rgba(255,255,255,0.03)" }} {...props}>{children}</thead>;
          },
          th({ children, ...props }) {
            return <th style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", padding: "12px 16px", textAlign: "left", color: "var(--accent-cyan)", fontWeight: "600" }} {...props}>{children}</th>;
          },
          td({ children, ...props }) {
            return <td style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", padding: "10px 16px", color: "var(--text-secondary)" }} {...props}>{children}</td>;
          },
          ul({ children, ...props }) {
            return <ul style={{ listStyleType: "disc", paddingLeft: "24px", margin: "12px 0", color: "var(--text-secondary)" }} {...props}>{children}</ul>;
          },
          ol({ children, ...props }) {
            return <ol style={{ listStyleType: "decimal", paddingLeft: "24px", margin: "12px 0", color: "var(--text-secondary)" }} {...props}>{children}</ol>;
          },
          li({ children, ...props }) {
            let text = "";
            if (Array.isArray(children)) {
              text = children.map(c => typeof c === 'string' ? c : '').join('');
            } else if (typeof children === 'string') {
              text = children;
            } else if (children && typeof children === 'object' && 'props' in children && (children as any).props.children) {
              text = (children as any).props.children;
            }
            
            const cleanLine = text.trim();
            const actions = ["Summarize", "Explain", "Generate Notes", "Create MCQs", "Ask Questions"];
            
            if (actions.includes(cleanLine) && onSendHint) {
              return (
                <li style={{ listStyleType: "none", margin: "8px 0", marginLeft: "-24px" }}>
                  <button
                    onClick={() => {
                      let query = "";
                      if (cleanLine === "Summarize") query = "Summarize the uploaded document";
                      else if (cleanLine === "Explain") query = "Explain the uploaded document";
                      else if (cleanLine === "Generate Notes") query = "Generate notes for the uploaded document";
                      else if (cleanLine === "Create MCQs") query = "Create MCQs for the uploaded document";
                      else if (cleanLine === "Ask Questions") query = "What questions can I ask about this document?";
                      onSendHint(query);
                    }}
                    style={{
                      background: "rgba(6, 214, 214, 0.05)",
                      border: "1px solid rgba(6, 214, 214, 0.15)",
                      color: "var(--accent-cyan)",
                      padding: "8px 16px",
                      borderRadius: "12px",
                      cursor: "pointer",
                      fontSize: "13px",
                      fontWeight: "600",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "8px",
                      transition: "all 0.2s ease",
                      outline: "none",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(6, 214, 214, 0.12)";
                      e.currentTarget.style.borderColor = "var(--accent-cyan)";
                      e.currentTarget.style.boxShadow = "0 0 12px rgba(6, 214, 214, 0.25)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(6, 214, 214, 0.05)";
                      e.currentTarget.style.borderColor = "rgba(6, 214, 214, 0.15)";
                      e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
                    }}
                  >
                    ✨ {cleanLine}
                  </button>
                </li>
              );
            }
            
            return <li style={{ margin: "4px 0", paddingLeft: "4px" }} {...props}>{children}</li>;
          },
          a({ children, href, ...props }) {
            if (href && (href.includes('/api/v1/projects/download') || href.includes('/api/v1/research/download'))) {
              return (
                <a
                  href="#"
                  onClick={async (e) => {
                    e.preventDefault();
                    try {
                      const token = localStorage.getItem("aura_access_token") || "";
                      const resp = await fetch(href, {
                        headers: { "Authorization": `Bearer ${token}` }
                      });
                      if (!resp.ok) throw new Error("Download failed");
                      const blob = await resp.blob();
                      const blobUrl = window.URL.createObjectURL(blob);
                      const link = document.createElement("a");
                      link.href = blobUrl;
                      
                      let filename = "download.zip";
                      const contentDisposition = resp.headers.get("Content-Disposition");
                      if (contentDisposition && contentDisposition.includes("filename=")) {
                        const matches = /filename="?([^"]+)"?/.exec(contentDisposition);
                        if (matches && matches[1]) {
                          filename = matches[1];
                        }
                      } else {
                        try {
                          const urlParams = new URL(href).searchParams;
                          const slug = urlParams.get("slug");
                          if (slug) filename = `${slug}.zip`;
                        } catch(e) {}
                      }
                      
                      link.download = filename;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      window.URL.revokeObjectURL(blobUrl);
                    } catch (err) {
                      console.error(err);
                      alert("Download failed. Please check authentication or try again.");
                    }
                  }}
                  style={{ color: "var(--accent-cyan)", textDecoration: "underline", textUnderlineOffset: "2px", cursor: "pointer" }}
                  {...props}
                >
                  {children}
                </a>
              );
            }
            return <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-cyan)", textDecoration: "underline", textUnderlineOffset: "2px" }} {...props}>{children}</a>;
          },
          h1({ children, ...props }) {
            return <h1 style={{ fontSize: "22px", fontWeight: "700", marginTop: "24px", marginBottom: "16px", color: "var(--text-primary)" }} {...props}>{children}</h1>;
          },
          h2({ children, ...props }) {
            return <h2 style={{ fontSize: "18px", fontWeight: "600", marginTop: "20px", marginBottom: "12px", color: "var(--text-primary)" }} {...props}>{children}</h2>;
          },
          h3({ children, ...props }) {
            return <h3 style={{ fontSize: "16px", fontWeight: "600", marginTop: "16px", marginBottom: "10px", color: "var(--text-primary)" }} {...props}>{children}</h3>;
          },
          p({ children, ...props }) {
            return <p style={{ marginBottom: "12px", lineHeight: "1.7" }} {...props}>{children}</p>;
          },
          blockquote({ children, ...props }) {
            return <blockquote style={{ borderLeft: "4px solid var(--accent-purple)", paddingLeft: "16px", margin: "16px 0", color: "var(--text-muted)", fontStyle: "italic", background: "rgba(255,255,255,0.02)", padding: "12px 16px", borderRadius: "0 8px 8px 0" }} {...props}>{children}</blockquote>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

interface ThinkingStep {
  step: string;
  status: string;
  detail: string;
}

function LiveStatusBar({ thinking, isStreaming }: { thinking: ThinkingStep[]; isStreaming?: boolean }) {
  if (!thinking || thinking.length === 0) return null;

  const activeStep = thinking.find((t) => t.status === "running");
  const completedCount = thinking.filter((t) => t.status === "completed" || t.status === "skipped").length;
  const progressPercent = Math.round((completedCount / thinking.length) * 100);
  const isDone = progressPercent === 100 || (!isStreaming && completedCount > 0);

  const displayStep = activeStep ? activeStep.step : (isDone ? "Completed" : "Processing...");

  return (
    <div
      style={{
        width: "100%",
        maxWidth: "280px",
        padding: "8px 12px",
        borderRadius: "8px",
        background: "rgba(255, 255, 255, 0.02)",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        marginBottom: "10px",
        overflow: "hidden"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {isDone ? (
            <Check size={12} color="#34d399" />
          ) : (
            <LoaderCircle size={12} color="var(--accent-cyan)" className="animate-spin" />
          )}
          <span style={{ fontSize: "11px", fontWeight: "600", color: isDone ? "#34d399" : "var(--accent-cyan)" }}>
            {displayStep}
          </span>
        </div>
        <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
          {progressPercent}%
        </span>
      </div>

      <div 
        style={{
          width: "100%",
          height: "3px",
          background: "rgba(255, 255, 255, 0.1)",
          borderRadius: "3px",
          overflow: "hidden"
        }}
      >
        <div
          style={{
            width: `${progressPercent}%`,
            height: "100%",
            background: isDone ? "#34d399" : "var(--accent-cyan)",
            borderRadius: "3px"
          }}
        />
      </div>
    </div>
  );
}

interface SearchMetrics {
  current_source: string;
  pages_read: number;
  docs_analyzed: number;
  sources_verified: number;
  confidence_score: number;
  estimated_remaining_time: number;
}

function DeepResearchProgressCard({ metrics, isCompleted }: { metrics: SearchMetrics, isCompleted?: boolean }) {
  const [isExpanded, setIsExpanded] = useState(!isCompleted);

  useEffect(() => {
    if (isCompleted) {
      setIsExpanded(false);
    }
  }, [isCompleted]);

  if (!metrics) return null;

  const isLowQuality = isCompleted && metrics.confidence_score > 0 && metrics.confidence_score < 50;

  if (!isExpanded) {
    return (
      <div
        onClick={() => setIsExpanded(true)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 12px",
          borderRadius: "20px",
          background: "var(--surface-glass)",
          border: "1px solid var(--surface-border)",
          cursor: "pointer",
          marginBottom: "16px",
          transition: "all 0.2s"
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = "var(--surface-glass-hover)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "var(--surface-glass)"; }}
      >
        <Check size={14} color="#10b981" />
        <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)" }}>
          Research Completed • {metrics.pages_read || 0} Sources Analyzed
        </span>
        {isLowQuality && (
          <div style={{ display: "flex", alignItems: "center", gap: "4px", marginLeft: "4px" }}>
            <AlertCircle size={12} color="#ef4444" />
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        width: "100%",
        padding: "16px",
        borderRadius: "8px",
        background: "var(--bg-elevated)",
        border: "1px solid var(--surface-border)",
        marginBottom: "16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid var(--surface-border)", paddingBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isCompleted ? (
            <Check size={16} color="#10b981" />
          ) : (
            <Compass size={16} className="animate-spin" color="var(--accent-cyan)" style={{ animationDuration: "3s" }} />
          )}
          <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>
            {isCompleted ? "Research Completed" : "Deep Research Active"}
          </span>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isLowQuality && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(239, 68, 68, 0.1)", padding: "4px 8px", borderRadius: "4px", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
              <AlertCircle size={12} color="#ef4444" />
              <span style={{ fontSize: "11px", fontWeight: "600", color: "#ef4444" }}>Low Consensus</span>
            </div>
          )}
          {isCompleted && (
            <button 
              onClick={() => setIsExpanded(false)}
              style={{ background: "transparent", border: "none", cursor: "pointer", display: "flex", alignItems: "center", color: "var(--text-muted)", outline: "none" }}
            >
              <ChevronUp size={16} />
            </button>
          )}
        </div>
      </div>

      <div 
        style={{ 
          display: "grid", 
          gridTemplateColumns: "repeat(3, 1fr)", 
          gap: "12px", 
          marginBottom: "16px"
        }}
      >
        <div>
          <div style={{ color: "var(--text-muted)", fontSize: "11px", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Sources Analyzed</div>
          <div style={{ fontSize: "16px", fontWeight: "500", color: "var(--text-primary)" }}>{metrics.pages_read || 0}</div>
        </div>
        <div>
          <div style={{ color: "var(--text-muted)", fontSize: "11px", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Facts Verified</div>
          <div style={{ fontSize: "16px", fontWeight: "500", color: "var(--text-primary)" }}>{metrics.sources_verified || 0}</div>
        </div>
        <div>
          <div style={{ color: "var(--text-muted)", fontSize: "11px", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Est. Time Left</div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ fontSize: "16px", fontWeight: "500", color: "var(--text-primary)" }}>
              {isCompleted ? "0s" : metrics.estimated_remaining_time ? `${metrics.estimated_remaining_time}s` : "--"}
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {metrics.confidence_score > 0 && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", marginBottom: "4px" }}>
              <span style={{ color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Confidence Score</span>
              <span style={{ fontWeight: "600", color: isLowQuality ? "#ef4444" : "var(--text-primary)" }}>{metrics.confidence_score}%</span>
            </div>
            <div style={{ width: "100%", height: "4px", background: "var(--surface-border)", borderRadius: "2px", overflow: "hidden" }}>
              <div 
                style={{ 
                  width: `${metrics.confidence_score}%`, 
                  height: "100%", 
                  background: isLowQuality ? "#ef4444" : "var(--text-primary)",
                  transition: "width 0.5s ease-out"
                }} 
              />
            </div>
          </div>
        )}

        {!isCompleted && metrics.current_source && (
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px", display: "flex", alignItems: "center", gap: "6px", background: "var(--surface-glass)", padding: "8px 12px", borderRadius: "6px" }}>
            <div style={{ width: "4px", height: "4px", borderRadius: "50%", background: "var(--accent-cyan)", flexShrink: 0, animation: "pulse 2s infinite" }} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {metrics.current_source}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

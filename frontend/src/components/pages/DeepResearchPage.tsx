/**
 * AURA OS Deep Research Page
 * Completely independent research interface with live progress,
 * publication-grade report rendering, source panel, and exports.
 */

"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Microscope, Search, Send, Square, Download, FileText, File, Copy,
  ExternalLink, Shield, Clock, ChevronRight, CheckCircle, Loader, Circle,
  History, ArrowLeft, X, Zap, BookOpen, Globe, Award, BarChart3,
} from "lucide-react";
import {
  startDeepResearch, cancelResearch, fetchResearchHistory,
  fetchResearchReport, getResearchDownloadUrl,
} from "@/lib/api";
import { parseSSEStream } from "@/lib/stream";
import type {
  ResearchDepth, ResearchSource, ResearchProgressStep,
  ResearchProgress, ResearchReport, ResearchMetrics,
} from "@/types";

// ── Depth Config ──
const DEPTH_OPTIONS: { value: ResearchDepth; label: string; desc: string; icon: React.ReactNode }[] = [
  { value: "quick", label: "Quick", desc: "3 sources, fast results", icon: <Zap size={14} /> },
  { value: "standard", label: "Standard", desc: "5 sources, balanced", icon: <Search size={14} /> },
  { value: "deep", label: "Deep", desc: "8 sources, thorough", icon: <BookOpen size={14} /> },
  { value: "expert", label: "Expert", desc: "12+ sources, maximum depth", icon: <Award size={14} /> },
];

export function DeepResearchPage() {
  // ── State ──
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");
  const [isResearching, setIsResearching] = useState(false);
  const [report, setReport] = useState("");
  const [progress, setProgress] = useState<ResearchProgress | null>(null);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [reportMeta, setReportMeta] = useState<any>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<ResearchReport[]>([]);
  const [showSourcePanel, setShowSourcePanel] = useState(true);
  const abortRef = useRef<(() => void) | null>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  // ── Load History ──
  const loadHistory = useCallback(async () => {
    try {
      const data = await fetchResearchHistory();
      setHistory(data);
    } catch (e) {
      console.warn("Failed to load research history:", e);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  // ── Start Research ──
  const handleStartResearch = useCallback(async () => {
    if (!topic.trim() || isResearching) return;

    setIsResearching(true);
    setReport("");
    setError(null);
    setSources([]);
    setReportMeta(null);
    setProgress(null);

    const { stream, abort } = startDeepResearch(topic, undefined, depth);
    abortRef.current = abort;

    try {
      await parseSSEStream(stream, {
        onConversationId: (id) => setConversationId(id),
        onToken: (token) => {
          setReport((prev) => prev + token);
        },
        onSearch: (_status, metadata) => {
          if (metadata) {
            setProgress(metadata as unknown as ResearchProgress);
            // Extract sources from final metadata
            const rm = metadata as any;
            if (rm?.research_report?.sources) {
              setSources(rm.research_report.sources);
              setReportMeta(rm.research_report);
              setShowSourcePanel(true);
            }
          }
        },
        onDone: () => {
          setIsResearching(false);
          loadHistory();
        },
        onError: (err) => {
          setError(err);
          setIsResearching(false);
        },
      });
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message);
      }
      setIsResearching(false);
    }
  }, [topic, depth, isResearching, loadHistory]);

  const handleStop = useCallback(() => {
    abortRef.current?.();
    if (conversationId) cancelResearch(conversationId);
    setIsResearching(false);
  }, [conversationId]);

  const handleCopyReport = useCallback(() => {
    navigator.clipboard.writeText(report);
  }, [report]);

  const handleLoadReport = useCallback(async (r: ResearchReport) => {
    try {
      const full = await fetchResearchReport(r.id);
      setReport(full.report_content || "");
      setSources(full.sources || []);
      setReportMeta(full);
      setTopic(r.topic);
      setShowHistory(false);
      setShowSourcePanel(true);
    } catch (e) {
      console.warn("Failed to load report:", e);
    }
  }, []);

  // ── Auto-scroll report ──
  useEffect(() => {
    if (reportRef.current && isResearching) {
      reportRef.current.scrollTop = reportRef.current.scrollHeight;
    }
  }, [report, isResearching]);

  // ── Render ──
  return (
    <div style={{
      display: "flex",
      width: "100%",
      height: "100%",
      background: "var(--bg-void)",
      overflow: "hidden",
    }}>
      {/* ═══ Main Content Area ═══ */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
        minWidth: 0,
      }}>
        {/* ── Header ── */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: 36, height: 36, borderRadius: "10px",
              background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Microscope size={20} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                AURA Deep Research
              </h1>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", letterSpacing: "0.5px" }}>
                Publication-grade research reports
              </span>
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadHistory(); }}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                padding: "8px 14px", borderRadius: "8px", fontSize: "12px",
                background: showHistory ? "rgba(139,92,246,0.15)" : "rgba(255,255,255,0.05)",
                color: showHistory ? "#a78bfa" : "var(--text-secondary)",
                border: "1px solid rgba(255,255,255,0.08)",
                cursor: "pointer", transition: "all 0.2s",
              }}
            >
              <History size={14} /> History
            </button>
          </div>
        </div>

        {/* ── History Panel ── */}
        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ overflow: "hidden", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
              <div style={{ padding: "16px 24px", maxHeight: "200px", overflowY: "auto" }}>
                {history.length === 0 ? (
                  <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>No research history yet.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {history.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => handleLoadReport(r)}
                        style={{
                          display: "flex", justifyContent: "space-between", alignItems: "center",
                          padding: "10px 14px", borderRadius: "8px", cursor: "pointer",
                          background: "rgba(255,255,255,0.03)",
                          border: "1px solid rgba(255,255,255,0.06)",
                          color: "var(--text-primary)", fontSize: "13px",
                          textAlign: "left", transition: "all 0.2s",
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(139,92,246,0.08)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                      >
                        <div>
                          <span style={{ fontWeight: 600 }}>{r.topic}</span>
                          <span style={{ color: "var(--text-muted)", marginLeft: "8px", fontSize: "11px" }}>
                            {r.depth} • {new Date(r.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <ChevronRight size={14} color="var(--text-muted)" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Input & Content Area ── */}
        {!report && !isResearching ? (
          /* ── Empty State: Research Input ── */
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            padding: "40px 24px", paddingBottom: "15vh",
          }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ textAlign: "center", maxWidth: "640px", width: "100%" }}
            >
              <div style={{
                width: 64, height: 64, borderRadius: "16px", margin: "0 auto 24px",
                background: "linear-gradient(135deg, #8b5cf6, #6366f1, #4f46e5)",
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 0 40px rgba(139,92,246,0.3)",
              }}>
                <Microscope size={32} color="#fff" />
              </div>
              <h2 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                Deep Research
              </h2>
              <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "32px", lineHeight: 1.6 }}>
                Enter any topic. AURA will search, read, verify, analyze, and generate
                a publication-grade research report with real citations.
              </p>

              {/* Depth Selector */}
              <div style={{
                display: "flex", gap: "8px", justifyContent: "center", marginBottom: "20px", flexWrap: "wrap",
              }}>
                {DEPTH_OPTIONS.map((d) => (
                  <button
                    key={d.value}
                    onClick={() => setDepth(d.value)}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px",
                      padding: "8px 16px", borderRadius: "20px", fontSize: "12px",
                      background: depth === d.value ? "rgba(139,92,246,0.2)" : "rgba(255,255,255,0.04)",
                      color: depth === d.value ? "#a78bfa" : "var(--text-muted)",
                      border: depth === d.value ? "1px solid rgba(139,92,246,0.4)" : "1px solid rgba(255,255,255,0.08)",
                      cursor: "pointer", transition: "all 0.2s", fontWeight: depth === d.value ? 600 : 400,
                    }}
                    title={d.desc}
                  >
                    {d.icon} {d.label}
                  </button>
                ))}
              </div>

              {/* Input */}
              <div style={{
                display: "flex", gap: "8px", width: "100%",
              }}>
                <div style={{
                  flex: 1, position: "relative",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "14px",
                  transition: "all 0.3s",
                }}>
                  <input
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleStartResearch(); } }}
                    placeholder="Enter your research topic..."
                    style={{
                      width: "100%", padding: "14px 18px", fontSize: "14px",
                      background: "transparent", border: "none", outline: "none",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
                <button
                  onClick={handleStartResearch}
                  disabled={!topic.trim()}
                  style={{
                    width: "48px", height: "48px", borderRadius: "14px",
                    background: topic.trim() ? "linear-gradient(135deg, #8b5cf6, #6366f1)" : "rgba(255,255,255,0.05)",
                    border: "none", cursor: topic.trim() ? "pointer" : "not-allowed",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", transition: "all 0.2s",
                    boxShadow: topic.trim() ? "0 0 20px rgba(139,92,246,0.3)" : "none",
                  }}
                >
                  <Send size={18} />
                </button>
              </div>
            </motion.div>
          </div>
        ) : (
          /* ── Research in Progress / Report View ── */
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            {/* Progress Bar */}
            {isResearching && progress && (
              <div style={{
                padding: "16px 24px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                flexShrink: 0,
              }}>
                {/* Step Progress */}
                <div style={{ display: "flex", gap: "4px", alignItems: "center", marginBottom: "12px", flexWrap: "wrap" }}>
                  {(progress.steps || []).map((step, idx) => (
                    <div key={step.id} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <div style={{
                        display: "flex", alignItems: "center", gap: "4px",
                        padding: "4px 10px", borderRadius: "12px", fontSize: "11px",
                        background: step.status === "running" ? "rgba(139,92,246,0.15)" :
                          step.status === "completed" ? "rgba(34,197,94,0.1)" : "rgba(255,255,255,0.03)",
                        color: step.status === "running" ? "#a78bfa" :
                          step.status === "completed" ? "#4ade80" : "var(--text-muted)",
                        border: step.status === "running" ? "1px solid rgba(139,92,246,0.3)" : "1px solid transparent",
                        fontWeight: step.status === "running" ? 600 : 400,
                      }}>
                        {step.status === "completed" ? <CheckCircle size={10} /> :
                         step.status === "running" ? <Loader size={10} className="animate-spin" /> :
                         <Circle size={10} />}
                        <span>{step.label}</span>
                      </div>
                      {idx < (progress.steps || []).length - 1 && (
                        <ChevronRight size={10} color="var(--text-muted)" style={{ opacity: 0.3 }} />
                      )}
                    </div>
                  ))}
                </div>

                {/* Metrics Bar */}
                <div style={{
                  display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-muted)",
                }}>
                  <span>📄 {progress.metrics?.pages_read || 0} pages read</span>
                  <span>🔍 {progress.metrics?.sources_found || 0} sources</span>
                  <span>📊 {progress.metrics?.facts_extracted || 0} facts</span>
                  <span>✅ {progress.metrics?.facts_verified || 0} verified</span>
                  <span>⏱️ {progress.metrics?.elapsed_time || 0}s</span>
                </div>
              </div>
            )}

            {/* Report Content */}
            <div
              ref={reportRef}
              style={{
                flex: 1, overflowY: "auto", padding: "24px 32px",
                maxWidth: "100%",
              }}
              className="scrollbar-hide"
            >
              {report ? (
                <div style={{ maxWidth: "800px", margin: "0 auto" }}>
                  <div className="research-report-content" style={{ lineHeight: 1.8, fontSize: "14px", color: "var(--text-primary)" }}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => <h1 style={{ fontSize: "24px", fontWeight: 700, color: "var(--text-primary)", borderBottom: "2px solid rgba(139,92,246,0.3)", paddingBottom: "8px", marginTop: "32px", marginBottom: "16px" }}>{children}</h1>,
                        h2: ({ children }) => <h2 style={{ fontSize: "18px", fontWeight: 600, color: "var(--text-primary)", marginTop: "28px", marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "6px" }}>{children}</h2>,
                        h3: ({ children }) => <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-secondary)", marginTop: "20px", marginBottom: "8px" }}>{children}</h3>,
                        p: ({ children }) => <p style={{ marginBottom: "14px", lineHeight: 1.8 }}>{children}</p>,
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#a78bfa", textDecoration: "none", fontWeight: 500, borderBottom: "1px dotted rgba(167,139,250,0.4)" }}>
                            {children}
                          </a>
                        ),
                        ul: ({ children }) => <ul style={{ paddingLeft: "20px", marginBottom: "14px" }}>{children}</ul>,
                        ol: ({ children }) => <ol style={{ paddingLeft: "20px", marginBottom: "14px" }}>{children}</ol>,
                        li: ({ children }) => <li style={{ marginBottom: "6px" }}>{children}</li>,
                        strong: ({ children }) => <strong style={{ color: "var(--text-primary)", fontWeight: 600 }}>{children}</strong>,
                        table: ({ children }) => (
                          <div style={{ overflowX: "auto", marginBottom: "16px" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>{children}</table>
                          </div>
                        ),
                        th: ({ children }) => <th style={{ padding: "8px 12px", borderBottom: "2px solid rgba(139,92,246,0.3)", textAlign: "left", fontWeight: 600, color: "var(--text-primary)", background: "rgba(255,255,255,0.03)" }}>{children}</th>,
                        td: ({ children }) => <td style={{ padding: "8px 12px", borderBottom: "1px solid rgba(255,255,255,0.06)", color: "var(--text-secondary)" }}>{children}</td>,
                        blockquote: ({ children }) => (
                          <blockquote style={{ borderLeft: "3px solid #8b5cf6", paddingLeft: "16px", margin: "16px 0", color: "var(--text-muted)", fontStyle: "italic" }}>{children}</blockquote>
                        ),
                      }}
                    >
                      {report}
                    </ReactMarkdown>
                  </div>
                </div>
              ) : isResearching ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", opacity: 0.5 }}>
                  <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
                    Generating report...
                  </p>
                </div>
              ) : null}
            </div>

            {/* Export & Action Bar */}
            {(report || isResearching) && (
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "12px 24px",
                borderTop: "1px solid rgba(255,255,255,0.06)",
                flexShrink: 0,
              }}>
                <div style={{ display: "flex", gap: "8px" }}>
                  {isResearching ? (
                    <button
                      onClick={handleStop}
                      style={{
                        display: "flex", alignItems: "center", gap: "6px",
                        padding: "8px 16px", borderRadius: "8px", fontSize: "12px",
                        background: "rgba(239,68,68,0.15)", color: "#f87171",
                        border: "1px solid rgba(239,68,68,0.3)",
                        cursor: "pointer", transition: "all 0.2s",
                      }}
                    >
                      <Square size={12} fill="#f87171" /> Stop Research
                    </button>
                  ) : (
                    <button
                      onClick={() => { setReport(""); setTopic(""); setSources([]); setReportMeta(null); }}
                      style={{
                        display: "flex", alignItems: "center", gap: "6px",
                        padding: "8px 16px", borderRadius: "8px", fontSize: "12px",
                        background: "rgba(255,255,255,0.05)", color: "var(--text-secondary)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        cursor: "pointer", transition: "all 0.2s",
                      }}
                    >
                      <ArrowLeft size={12} /> New Research
                    </button>
                  )}
                </div>

                {report && !isResearching && (
                  <div style={{ display: "flex", gap: "6px" }}>
                    <ExportButton icon={<Copy size={13} />} label="Copy" onClick={handleCopyReport} />
                    {reportMeta?.markdown_path && (
                      <ExportButton icon={<FileText size={13} />} label="Markdown"
                        onClick={() => window.open(getResearchDownloadUrl(reportMeta.markdown_path), "_blank")} />
                    )}
                    {reportMeta?.docx_path && (
                      <ExportButton icon={<File size={13} />} label="DOCX"
                        onClick={() => window.open(getResearchDownloadUrl(reportMeta.docx_path), "_blank")} />
                    )}
                    {reportMeta?.pdf_path && (
                      <ExportButton icon={<Download size={13} />} label="PDF"
                        onClick={() => window.open(getResearchDownloadUrl(reportMeta.pdf_path), "_blank")} />
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ═══ Source Panel (Right Sidebar) ═══ */}
      {showSourcePanel && sources.length > 0 && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          style={{
            width: 320, flexShrink: 0,
            borderLeft: "1px solid rgba(255,255,255,0.06)",
            display: "flex", flexDirection: "column",
            background: "rgba(0,0,0,0.2)",
            overflow: "hidden",
          }}
        >
          {/* Source Panel Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Globe size={16} color="#a78bfa" />
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                Sources ({sources.length})
              </span>
            </div>
            <button
              onClick={() => setShowSourcePanel(false)}
              style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "4px" }}
            >
              <X size={14} />
            </button>
          </div>

          {/* Source List */}
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }} className="scrollbar-hide">
            {sources.map((source, idx) => (
              <a
                key={idx}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "block", padding: "12px",
                  borderRadius: "10px", marginBottom: "6px",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.05)",
                  textDecoration: "none",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(139,92,246,0.06)"; e.currentTarget.style.borderColor = "rgba(139,92,246,0.2)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.05)"; }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: "6px", flexShrink: 0,
                    background: "rgba(139,92,246,0.1)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginTop: "2px",
                  }}>
                    <SourceIcon category={source.category} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: "12px", fontWeight: 600, color: "var(--text-primary)",
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                      marginBottom: "3px",
                    }}>
                      {source.title}
                    </div>
                    <div style={{
                      fontSize: "11px", color: "var(--text-muted)",
                      display: "flex", alignItems: "center", gap: "6px",
                    }}>
                      <span>{source.domain}</span>
                      <span style={{ opacity: 0.4 }}>•</span>
                      <TrustBadge score={source.trust_score} />
                    </div>
                    <div style={{
                      display: "flex", alignItems: "center", gap: "6px", marginTop: "4px",
                    }}>
                      <span style={{
                        fontSize: "10px", padding: "2px 6px", borderRadius: "4px",
                        background: "rgba(139,92,246,0.1)", color: "#a78bfa",
                      }}>
                        {source.category}
                      </span>
                      {source.publication_date && (
                        <span style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "2px" }}>
                          <Clock size={9} /> {source.publication_date}
                        </span>
                      )}
                    </div>
                  </div>
                  <ExternalLink size={12} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: "4px" }} />
                </div>
              </a>
            ))}
          </div>

          {/* Quality Score */}
          {reportMeta?.quality && (
            <div style={{
              padding: "12px 16px",
              borderTop: "1px solid rgba(255,255,255,0.06)",
            }}>
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                marginBottom: "6px",
              }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Quality Score</span>
                <span style={{
                  fontSize: "13px", fontWeight: 700,
                  color: reportMeta.quality.quality_score >= 70 ? "#4ade80" :
                    reportMeta.quality.quality_score >= 50 ? "#fbbf24" : "#f87171",
                }}>
                  {reportMeta.quality.quality_score}/100
                </span>
              </div>
              <div style={{
                height: "4px", borderRadius: "2px", background: "rgba(255,255,255,0.06)",
                overflow: "hidden",
              }}>
                <div style={{
                  height: "100%", borderRadius: "2px",
                  width: `${reportMeta.quality.quality_score}%`,
                  background: reportMeta.quality.quality_score >= 70 ? "linear-gradient(90deg, #4ade80, #22c55e)" :
                    reportMeta.quality.quality_score >= 50 ? "linear-gradient(90deg, #fbbf24, #f59e0b)" :
                    "linear-gradient(90deg, #f87171, #ef4444)",
                  transition: "width 0.5s",
                }} />
              </div>
              <div style={{
                display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "8px",
              }}>
                <QualityChip label="Citations" ok={reportMeta.quality.has_citations} />
                <QualityChip label="Sources" ok={reportMeta.quality.has_sources} />
                <QualityChip label="Summary" ok={reportMeta.quality.has_executive_summary} />
                <QualityChip label="Conclusion" ok={reportMeta.quality.has_conclusion} />
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Error Toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            style={{
              position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)",
              padding: "12px 20px", borderRadius: "10px",
              background: "rgba(239,68,68,0.15)", color: "#f87171",
              border: "1px solid rgba(239,68,68,0.3)",
              fontSize: "13px", zIndex: 100,
              display: "flex", alignItems: "center", gap: "8px",
            }}
          >
            {error}
            <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer" }}>
              <X size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Helper Components ──

function ExportButton({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: "5px",
        padding: "6px 12px", borderRadius: "6px", fontSize: "11px",
        background: "rgba(255,255,255,0.05)", color: "var(--text-secondary)",
        border: "1px solid rgba(255,255,255,0.08)",
        cursor: "pointer", transition: "all 0.2s",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(139,92,246,0.1)"; e.currentTarget.style.color = "#a78bfa"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; e.currentTarget.style.color = "var(--text-secondary)"; }}
    >
      {icon} {label}
    </button>
  );
}

function TrustBadge({ score }: { score: number }) {
  const color = score >= 90 ? "#4ade80" : score >= 70 ? "#fbbf24" : score >= 50 ? "#fb923c" : "#94a3b8";
  const label = score >= 90 ? "High Trust" : score >= 70 ? "Good" : score >= 50 ? "Fair" : "Low";
  return (
    <span style={{
      display: "flex", alignItems: "center", gap: "3px",
      fontSize: "10px", color,
    }}>
      <Shield size={9} /> {score}% {label}
    </span>
  );
}

function QualityChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span style={{
      fontSize: "10px", padding: "2px 8px", borderRadius: "4px",
      background: ok ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
      color: ok ? "#4ade80" : "#f87171",
      display: "flex", alignItems: "center", gap: "3px",
    }}>
      {ok ? <CheckCircle size={9} /> : <X size={9} />} {label}
    </span>
  );
}

function SourceIcon({ category }: { category: string }) {
  const size = 14;
  const color = "#a78bfa";
  switch (category) {
    case "Research Paper": return <BookOpen size={size} color={color} />;
    case "Official Source": return <Shield size={size} color={color} />;
    case "News Article": return <BarChart3 size={size} color={color} />;
    case "Document": return <FileText size={size} color={color} />;
    default: return <Globe size={size} color={color} />;
  }
}

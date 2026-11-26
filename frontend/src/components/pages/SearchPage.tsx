/**
 * AURA OS Search Engine Control Panel
 * Cascading search interface, multi-provider selections, duplicate collapse,
 * LLM summaries, comparisons, and performance metrics.
 */

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Search,
  Globe,
  Clock,
  Trash2,
  Shield,
  BookOpen,
  Cpu,
  Database,
  Code,
  MessageSquare,
  FileText,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  ArrowRight
} from "lucide-react";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  content?: string;
  score: number;
  source_domain: string;
  provider: string;
  duplicates: SearchResultItem[];
}

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [searching, setSearching] = useState(false);
  
  // Custom Search Options
  const [cascade, setCascade] = useState(true);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([
    "duckduckgo", "wikipedia", "mdn", "stackoverflow", "reddit", "arxiv", "youtube", "github", "docs"
  ]);
  
  // Response Metadata
  const [summary, setSummary] = useState("");
  const [comparison, setComparison] = useState("");
  const [pathTaken, setPathTaken] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<{ searchTime: number; cached: boolean } | null>(null);
  
  // UI States
  const [expandedDuplicates, setExpandedDuplicates] = useState<number[]>([]);
  const [activeTab, setActiveTab] = useState<"summary" | "comparison" | "sources">("summary");
  const [cacheStats, setCacheStats] = useState<{ active_cached: number } | null>(null);
  const [loadingCache, setLoadingCache] = useState(false);
  
  const { showToast, showModal } = useNotification();

  const fetchCacheStats = useCallback(async () => {
    setLoadingCache(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/search/cache`);
      if (resp.ok) {
        const data = await resp.json();
        setCacheStats(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCache(false);
    }
  }, []);

  useEffect(() => {
    fetchCacheStats();
  }, [fetchCacheStats]);

  const handleProviderToggle = (providerId: string) => {
    setSelectedProviders((prev) =>
      prev.includes(providerId)
        ? prev.filter((p) => p !== providerId)
        : [...prev, providerId]
    );
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    setMetrics(null);
    setSummary("");
    setComparison("");
    setPathTaken([]);
    setResults([]);
    setExpandedDuplicates([]);
    
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          cascade,
          providers: selectedProviders,
          max_results: 5,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResults(data.results || []);
        setSummary(data.summary || "");
        setComparison(data.comparison || "");
        setPathTaken(data.path_taken || []);
        setMetrics({
          searchTime: data.search_time || 0,
          cached: data.cached || false,
        });
        
        // Auto-select tab based on hits
        if (data.summary) {
          setActiveTab("summary");
        } else {
          setActiveTab("sources");
        }
        
        fetchCacheStats();
      } else {
        showToast("Search Engine query failed", "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Error connecting to search service", "error");
    } finally {
      setSearching(false);
    }
  };

  const toggleExpandDuplicates = (index: number) => {
    setExpandedDuplicates((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const executeClearCache = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/search/cache`, { method: "DELETE" });
      if (resp.ok) {
        showToast("Search cache flushed successfully", "success");
        fetchCacheStats();
      } else {
        showToast("Failed to clear search cache", "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Error clearing search cache", "error");
    }
  };

  const handleClearCache = () => {
    showModal({
      title: "Clear Search Cache",
      description: "Are you sure you want to flush all cached web search queries?",
      actions: [
        {
          label: "Clear Cache",
          variant: "danger",
          onClick: executeClearCache
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const renderSummaryWithCitations = (text: string) => {
    if (!text) return null;
    
    // Split text based on numbered bracket patterns e.g. [1], [2]
    const parts = text.split(/(\[\d+\])/g);
    
    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const num = parseInt(match[1], 10);
        const targetResult = results[num - 1];
        
        return (
          <a
            key={i}
            href={targetResult ? targetResult.url : "#"}
            target="_blank"
            rel="noopener noreferrer"
            title={targetResult ? `[${num}] ${targetResult.title} (${targetResult.provider})` : `Source [${num}]`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "15px",
              height: "15px",
              fontSize: "8.5px",
              fontWeight: "700",
              borderRadius: "50%",
              background: "var(--accent-cyan)",
              color: "#000",
              margin: "0 2px",
              textDecoration: "none",
              verticalAlign: "super",
              cursor: "pointer",
              boxShadow: "var(--glow-cyan)",
              transition: "transform 0.15s"
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "scale(1.2)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1.0)";
            }}
          >
            {num}
          </a>
        );
      }
      return part;
    });
  };

  const PROVIDERS_METADATA = [
    { id: "google", name: "Google", icon: Globe, color: "var(--accent-cyan)" },
    { id: "bing", name: "Bing", icon: Globe, color: "var(--accent-cyan)" },
    { id: "duckduckgo", name: "DuckDuckGo", icon: Search, color: "var(--accent-cyan)" },
    { id: "wikipedia", name: "Wikipedia", icon: BookOpen, color: "var(--accent-purple)" },
    { id: "mdn", name: "MDN Docs", icon: Cpu, color: "var(--accent-purple)" },
    { id: "github", name: "GitHub", icon: Code, color: "var(--accent-purple)" },
    { id: "stackoverflow", name: "StackOverflow", icon: Database, color: "var(--accent-purple)" },
    { id: "reddit", name: "Reddit", icon: MessageSquare, color: "var(--accent-purple)" },
    { id: "arxiv", name: "ArXiv Research", icon: FileText, color: "var(--accent-purple)" },
    { id: "youtube", name: "YouTube", icon: Globe, color: "var(--accent-purple)" },
    { id: "docs", name: "Official Docs", icon: BookOpen, color: "var(--accent-purple)" },
  ];

  return (
    <div
      style={{
        padding: "20px",
        height: "100%",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        background: "rgba(6, 6, 12, 0.25)"
      }}
    >
      {/* Header */}
      <div>
        <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", letterSpacing: "0.5px" }}>
          🌐 AURA CASCADING SEARCH ENGINE
        </span>
        <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "4px" }}>
          Queries chat memory, workspace knowledge docs, and multiple web APIs concurrently.
        </p>
      </div>

      {/* Settings Grid (Glass Panel) */}
      <div
        style={{
          background: "rgba(255, 255, 255, 0.01)",
          border: "1px solid rgba(255, 255, 255, 0.04)",
          borderRadius: "8px",
          padding: "14px",
          display: "flex",
          flexDirection: "column",
          gap: "12px"
        }}
      >
        {/* Cascade Mode Toggle */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "500" }}>
            Priority Cascade Retrieval (Memory ➔ KB ➔ Web)
          </span>
          <label style={{ display: "inline-flex", alignItems: "center", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={cascade}
              onChange={(e) => setCascade(e.target.checked)}
              style={{
                width: "36px",
                height: "18px",
                appearance: "none",
                background: cascade ? "var(--accent-cyan)" : "rgba(255, 255, 255, 0.1)",
                borderRadius: "9px",
                position: "relative",
                outline: "none",
                transition: "background 0.2s",
                cursor: "pointer"
              }}
            />
            <span
              style={{
                width: "14px",
                height: "14px",
                background: "#000",
                borderRadius: "50%",
                position: "absolute",
                transform: cascade ? "translateX(18px)" : "translateX(2px)",
                transition: "transform 0.2s"
              }}
            />
          </label>
        </div>

        {/* Providers grid */}
        <div>
          <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: "700", letterSpacing: "1px", textTransform: "uppercase" }}>
            Search Providers Selection
          </span>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))",
              gap: "6px",
              marginTop: "8px"
            }}
          >
            {PROVIDERS_METADATA.map((p) => {
              const Icon = p.icon;
              const isSelected = selectedProviders.includes(p.id);
              return (
                <button
                  key={p.id}
                  onClick={() => handleProviderToggle(p.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 10px",
                    borderRadius: "6px",
                    background: isSelected ? "rgba(6, 214, 214, 0.08)" : "rgba(255,255,255,0.01)",
                    border: isSelected ? "1px solid rgba(6, 214, 214, 0.3)" : "1px solid rgba(255,255,255,0.03)",
                    color: isSelected ? "var(--text-primary)" : "var(--text-muted)",
                    fontSize: "11px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    textAlign: "left"
                  }}
                >
                  <Icon size={12} style={{ color: isSelected ? p.color : "var(--text-muted)" }} />
                  <span>{p.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Query input Form */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: "10px" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search query topic..."
            style={{
              width: "100%",
              padding: "10px 14px 10px 36px",
              borderRadius: "8px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.04)",
              color: "var(--text-primary)",
              outline: "none",
              fontSize: "13px"
            }}
          />
          <Search size={14} style={{ position: "absolute", left: "12px", top: "13px", color: "var(--text-muted)" }} />
        </div>
        <button
          type="submit"
          disabled={searching || selectedProviders.length === 0}
          style={{
            padding: "10px 18px",
            background: "var(--accent-cyan)",
            color: "#000",
            border: "none",
            borderRadius: "8px",
            fontSize: "13px",
            fontWeight: "600",
            cursor: "pointer",
            opacity: selectedProviders.length === 0 ? 0.5 : 1,
            boxShadow: "var(--glow-cyan)"
          }}
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Path tracker and performance metrics */}
      {searching && (
        <div
          style={{
            padding: "12px",
            borderRadius: "8px",
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.02)",
            fontSize: "11px",
            fontFamily: "monospace",
            color: "var(--accent-cyan)",
            display: "flex",
            flexDirection: "column",
            gap: "4px"
          }}
        >
          <div>➜ Checking short-term conversation memories...</div>
          <div>➜ Checking knowledge base vectors...</div>
          <div>➜ Gathering web results from: {selectedProviders.join(", ")}...</div>
        </div>
      )}

      {pathTaken.length > 0 && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "8px",
            background: "rgba(255,255,255,0.01)",
            border: "1px solid rgba(255,255,255,0.03)",
            fontSize: "11px",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
            color: "var(--text-muted)"
          }}
        >
          <span style={{ fontWeight: "700", fontSize: "9px", letterSpacing: "1px", textTransform: "uppercase" }}>
            🔍 Query Search Path
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px", marginTop: "4px" }}>
            {pathTaken.map((step, sIdx) => (
              <React.Fragment key={sIdx}>
                {sIdx > 0 && <ArrowRight size={10} />}
                <span
                  style={{
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: step.includes("hit") ? "rgba(16, 185, 129, 0.1)" : "rgba(255,255,255,0.03)",
                    border: step.includes("hit") ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(255,255,255,0.05)",
                    color: step.includes("hit") ? "#34d399" : "var(--text-secondary)"
                  }}
                >
                  {step === "memory_hit" && "✅ Memory Hit"}
                  {step === "memory_skipped" && "Memory Skipped"}
                  {step === "kb_hit" && "✅ KB Document Hit"}
                  {step === "kb_skipped" && "KB Skipped"}
                  {step === "web_search" && "🌐 Web Query"}
                  {step === "memory_error" && "⚠️ Memory Error"}
                  {step === "kb_error" && "⚠️ KB Error"}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {metrics && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "8px",
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.04)",
            display: "flex",
            gap: "20px",
            fontSize: "11.5px",
            color: "var(--text-secondary)"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Clock size={12} style={{ color: "var(--accent-cyan)" }} />
            <span>Latency: <strong>{metrics.searchTime.toFixed(2)}s</strong></span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Globe size={12} style={{ color: "var(--accent-purple)" }} />
            <span>Origin: <strong>{metrics.cached ? "Cached Query" : "Live Request"}</strong></span>
          </div>
        </div>
      )}

      {/* Tabs */}
      {(summary || comparison || results.length > 0) && (
        <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.05)", gap: "10px" }}>
          {summary && (
            <button
              onClick={() => setActiveTab("summary")}
              style={{
                padding: "8px 14px",
                background: "none",
                border: "none",
                borderBottom: activeTab === "summary" ? "2px solid var(--accent-cyan)" : "none",
                color: activeTab === "summary" ? "var(--text-primary)" : "var(--text-muted)",
                fontSize: "12px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              Summary Answer
            </button>
          )}
          {comparison && (
            <button
              onClick={() => setActiveTab("comparison")}
              style={{
                padding: "8px 14px",
                background: "none",
                border: "none",
                borderBottom: activeTab === "comparison" ? "2px solid var(--accent-cyan)" : "none",
                color: activeTab === "comparison" ? "var(--text-primary)" : "var(--text-muted)",
                fontSize: "12px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              Source Comparison
            </button>
          )}
          <button
            onClick={() => setActiveTab("sources")}
            style={{
              padding: "8px 14px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "sources" ? "2px solid var(--accent-cyan)" : "none",
              color: activeTab === "sources" ? "var(--text-primary)" : "var(--text-muted)",
              fontSize: "12px",
              fontWeight: "600",
              cursor: "pointer"
            }}
          >
            Sources ({results.length})
          </button>
        </div>
      )}

      {/* Main content body */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "14px" }}>
        {searching ? (
          <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "60px", fontSize: "13px" }}>
            AURA is executing priority cascade retrieval...
          </div>
        ) : results.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "60px", fontSize: "13px" }}>
            Search query to view results and analysis.
          </div>
        ) : activeTab === "summary" && summary ? (
          <div
            style={{
              padding: "16px",
              borderRadius: "8px",
              background: "rgba(255, 255, 255, 0.01)",
              border: "1px solid rgba(255, 255, 255, 0.03)",
              color: "var(--text-secondary)",
              fontSize: "13px",
              lineHeight: "1.6",
              whiteSpace: "pre-wrap"
            }}
          >
            {renderSummaryWithCitations(summary)}
          </div>
        ) : activeTab === "comparison" && comparison ? (
          <div
            style={{
              padding: "16px",
              borderRadius: "8px",
              background: "rgba(255, 255, 255, 0.01)",
              border: "1px solid rgba(255, 255, 255, 0.03)",
              color: "var(--text-secondary)",
              fontSize: "13px",
              lineHeight: "1.6",
              whiteSpace: "pre-wrap"
            }}
          >
            {comparison}
          </div>
        ) : (
          /* Results/Sources list */
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {results.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: "14px",
                  borderRadius: "8px",
                  background: "rgba(255,255,255,0.01)",
                  border: "1px solid rgba(255,255,255,0.03)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px"
                }}
              >
                {/* Header line with Provider badge */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: "var(--accent-cyan)",
                      fontSize: "13px",
                      fontWeight: "600",
                      textDecoration: "none",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "75%"
                    }}
                  >
                    [{idx + 1}] 🔗 {item.title}
                  </a>
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: "700",
                      background: "rgba(255, 255, 255, 0.06)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      color: "var(--text-secondary)",
                      padding: "2px 6px",
                      borderRadius: "4px"
                    }}
                  >
                    {item.provider}
                  </span>
                </div>
                
                <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                  {item.url && item.url.startsWith("http") ? new URL(item.url).hostname : item.url}
                </span>

                <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: "1.4" }}>
                  {item.snippet}
                </p>

                {/* Duplicates block */}
                {item.duplicates && item.duplicates.length > 0 && (
                  <div
                    style={{
                      marginTop: "4px",
                      borderLeft: "2px solid rgba(6, 214, 214, 0.2)",
                      paddingLeft: "10px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px"
                    }}
                  >
                    <button
                      onClick={() => toggleExpandDuplicates(idx)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--accent-cyan)",
                        fontSize: "11px",
                        cursor: "pointer",
                        padding: 0,
                        textAlign: "left",
                        width: "fit-content"
                      }}
                    >
                      {expandedDuplicates.includes(idx)
                        ? "Hide duplicate sources"
                        : `Show ${item.duplicates.length} duplicate source(s)...`}
                    </button>
                    {expandedDuplicates.includes(idx) && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "4px" }}>
                        {item.duplicates.map((dup, dIdx) => (
                          <div key={dIdx} style={{ fontSize: "11px" }}>
                            <a
                              href={dup.url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: "var(--text-secondary)", textDecoration: "none" }}
                            >
                              🔗 {dup.title}
                            </a>
                            <span
                              style={{
                                marginLeft: "6px",
                                fontSize: "8.5px",
                                background: "rgba(255, 255, 255, 0.04)",
                                color: "var(--text-muted)",
                                padding: "1px 4px",
                                borderRadius: "3px"
                              }}
                            >
                              {dup.provider}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cache controller footer */}
      <div
        style={{
          borderTop: "1px solid rgba(255,255,255,0.03)",
          paddingTop: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Shield size={14} style={{ color: "var(--text-muted)" }} />
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {cacheStats ? `Cached Queries: ${cacheStats.active_cached}` : "Fetching cache stats..."}
          </span>
        </div>
        
        <button
          onClick={handleClearCache}
          disabled={loadingCache}
          style={{
            background: "none",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            color: "#f87171",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "11.5px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            cursor: "pointer"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(239, 68, 68, 0.08)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "none";
          }}
        >
          <Trash2 size={12} />
          <span>Clear Cache</span>
        </button>
      </div>
    </div>
  );
}

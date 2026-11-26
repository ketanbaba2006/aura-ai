/**
 * AURA OS Long-term Memory Dashboard Page
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { MemorySearchResult } from "@/types";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

export function MemoryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MemorySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);
  const { showToast } = useNotification();

  const handleSearch = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setError(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/memory/search/?q=${encodeURIComponent(searchQuery)}&limit=10`);
      if (!resp.ok) {
        throw new Error(`Memory search failed: ${resp.statusText}`);
      }
      const data = await resp.json();
      setSearchResults(data);
    } catch (err: any) {
      setError(err.message || "Failed to search memories.");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery]);

  const handleClearMemory = async () => {
    setError(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const conversationsResp = await fetchWithAuth(`${apiBase}/conversations`);
      if (!conversationsResp.ok) throw new Error("Could not fetch conversations to clear memory");
      const conversations = await conversationsResp.json();
      
      // Delete memory of each conversation
      for (const c of conversations) {
        const delResp = await fetchWithAuth(`${apiBase}/conversations/${c.id}`, { method: "DELETE" });
        if (!delResp.ok) console.error(`Failed to delete conversation ${c.id}`);
      }
      
      setSearchResults([]);
      setClearConfirm(false);
      showToast("All conversation memory cleared.", "success");
    } catch (err: any) {
      setError(err.message || "Failed to clear memory database.");
    }
  };

  return (
    <div className="page-container" style={{ padding: "40px", height: "100%", overflowY: "auto" }}>
      <div className="page-header" style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "600", color: "var(--text)", marginBottom: "8px" }}>
          🧠 Memory Engine
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
          Inspect and search AURA's long-term semantic memory database.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "24px" }}>
        {/* Search Panel */}
        <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Semantic Similarity Query</h2>
          
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
            <input
              type="text"
              className="chat-input-field"
              placeholder="Type query to retrieve matching conversation statements..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                outline: "none",
                fontSize: "14px"
              }}
            />
            <button
              type="submit"
              disabled={isSearching}
              style={{
                padding: "12px 24px",
                borderRadius: "8px",
                background: "var(--primary)",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontWeight: "500",
                fontSize: "14px"
              }}
            >
              {isSearching ? "Querying..." : "Search"}
            </button>
          </form>

          {error && (
            <div style={{ padding: "12px", borderRadius: "6px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--error)", color: "var(--error)", marginBottom: "20px", fontSize: "14px" }}>
              {error}
            </div>
          )}

          {/* Results */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {searchResults.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px", fontSize: "14px" }}>
                {searchQuery ? "No matching semantic memories retrieved." : "Enter a search term to query memories."}
              </div>
            ) : (
              searchResults.map((result, idx) => (
                <div
                  key={result.message_id || idx}
                  style={{
                    padding: "16px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontWeight: "600",
                        textTransform: "uppercase",
                        background: result.role === "user" ? "rgba(59, 130, 246, 0.2)" : "rgba(16, 185, 129, 0.2)",
                        color: result.role === "user" ? "#60a5fa" : "#34d399"
                      }}
                    >
                      {result.role}
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>
                      Relevance: <strong style={{ color: "var(--primary)" }}>{(result.relevance * 100).toFixed(1)}%</strong>
                    </span>
                  </div>
                  <div style={{ color: "var(--text)", fontSize: "14px", lineHeight: "1.5" }}>
                    {result.content}
                  </div>
                  <div style={{ color: "var(--text-muted)", fontSize: "11px", textAlign: "right" }}>
                    {new Date(result.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Database Cleaners */}
        <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", borderTop: "2px solid var(--error)" }}>
          <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "8px" }}>Memory Maintenance</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "20px" }}>
            Danger Area: Purging conversation memory will clear SQLite records and delete all long-term semantic search vectors.
          </p>

          {!clearConfirm ? (
            <button
              onClick={() => setClearConfirm(true)}
              style={{
                padding: "10px 20px",
                borderRadius: "6px",
                background: "rgba(239, 68, 68, 0.15)",
                color: "#f87171",
                border: "1px solid var(--error)",
                cursor: "pointer",
                fontWeight: "500",
                fontSize: "13px"
              }}
            >
              Clear Memory Database
            </button>
          ) : (
            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <span style={{ fontSize: "13px", color: "var(--error)" }}>Are you sure? This cannot be undone.</span>
              <button
                onClick={handleClearMemory}
                style={{
                  padding: "8px 16px",
                  borderRadius: "6px",
                  background: "var(--error)",
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: "600",
                  fontSize: "13px"
                }}
              >
                Yes, Purge
              </button>
              <button
                onClick={() => setClearConfirm(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "6px",
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "var(--text)",
                  border: "1px solid var(--border)",
                  cursor: "pointer",
                  fontSize: "13px"
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * AURA OS Activity Logs Dashboard Page
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { ActivityLog } from "@/types";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

export function LogsPage() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { showToast, showModal } = useNotification();

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      let url = `${apiBase}/logs?limit=50`;
      if (category) url += `&category=${category}`;
      if (status) url += `&status=${status}`;

      const resp = await fetchWithAuth(url);
      if (resp.ok) {
        const data = await resp.json();
        setLogs(data);
      }
    } catch (e) {
      console.error("Failed to load logs", e);
    } finally {
      setIsLoading(false);
    }
  }, [category, status]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handlePurgeLogs = () => {
    showModal({
      title: "Confirm Purge Logs",
      description: "Are you sure you want to clear all activity logs?",
      actions: [
        {
          label: "Purge Logs",
          variant: "danger",
          onClick: executePurgeLogs
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const executePurgeLogs = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/logs`, { method: "DELETE" });
      if (resp.ok) {
        setLogs([]);
        showToast("Activity logs successfully cleared.", "success");
      }
    } catch (e) {
      showToast("Failed to clear activity logs.", "error");
      console.error("Failed to clear logs", e);
    }
  };

  const getStatusColor = (level: string) => {
    switch (level) {
      case "success": return "#34d399";
      case "error": return "#f87171";
      default: return "#60a5fa";
    }
  };

  return (
    <div className="page-container" style={{ padding: "40px", height: "100%", overflowY: "auto" }}>
      <div className="page-header" style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: "600", color: "var(--text)", marginBottom: "8px" }}>
            📑 Activity Logs
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Real-time auditable stream of agent operations, tool calls, memory actions, and errors.
          </p>
        </div>
        
        <button
          onClick={handlePurgeLogs}
          style={{
            padding: "10px 18px",
            borderRadius: "8px",
            background: "rgba(239, 68, 68, 0.1)",
            color: "#f87171",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            cursor: "pointer",
            fontWeight: "500",
            fontSize: "13.5px"
          }}
        >
          Purge Log History
        </button>
      </div>

      {/* Filter panel */}
      <div
        className="chat-card"
        style={{
          padding: "16px 24px",
          borderRadius: "10px",
          background: "var(--card)",
          border: "1px solid var(--border)",
          display: "flex",
          gap: "16px",
          marginBottom: "24px"
        }}
      >
        <div style={{ display: "flex", flex: 1, flexDirection: "column", gap: "6px" }}>
          <label style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{
              padding: "10px",
              borderRadius: "6px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              fontSize: "13.5px",
              outline: "none"
            }}
          >
            <option value="">All Categories</option>
            <option value="router">Router</option>
            <option value="tools">Tools</option>
            <option value="search">Search</option>
            <option value="memory">Memory</option>
            <option value="planner">Planner</option>
            <option value="knowledge">Knowledge</option>
          </select>
        </div>

        <div style={{ display: "flex", flex: 1, flexDirection: "column", gap: "6px" }}>
          <label style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Severity Level</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            style={{
              padding: "10px",
              borderRadius: "6px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              fontSize: "13.5px",
              outline: "none"
            }}
          >
            <option value="">All Levels</option>
            <option value="info">Info</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Logs Table Card */}
      <div className="chat-card" style={{ borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", overflow: "hidden" }}>
        {isLoading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>Loading logs history...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: "80px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>
            No matching log records found in database.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13.5px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(255,255,255,0.01)" }}>
                  <th style={{ padding: "16px 20px", color: "var(--text-muted)", fontWeight: "500", textAlign: "left" }}>Timestamp</th>
                  <th style={{ padding: "16px 20px", color: "var(--text-muted)", fontWeight: "500", textAlign: "left" }}>Status</th>
                  <th style={{ padding: "16px 20px", color: "var(--text-muted)", fontWeight: "500", textAlign: "left" }}>Category</th>
                  <th style={{ padding: "16px 20px", color: "var(--text-muted)", fontWeight: "500", textAlign: "left" }}>Action Type</th>
                  <th style={{ padding: "16px 20px", color: "var(--text-muted)", fontWeight: "500", textAlign: "left" }}>Description</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const isExpanded = expandedId === log.id;
                  return (
                    <table key={log.id} style={{ display: "contents" }}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : log.id)}
                        style={{
                          borderBottom: "1px solid var(--border)",
                          cursor: "pointer",
                          background: isExpanded ? "rgba(255,255,255,0.02)" : "transparent",
                          transition: "background 0.2s"
                        }}
                      >
                        <td style={{ padding: "16px 20px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td style={{ padding: "16px 20px" }}>
                          <span
                            style={{
                              padding: "3px 8px",
                              borderRadius: "4px",
                              fontWeight: "600",
                              fontSize: "11px",
                              textTransform: "uppercase",
                              background: log.status === "error" ? "rgba(239, 68, 68, 0.15)" : log.status === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(59, 130, 246, 0.15)",
                              color: getStatusColor(log.status)
                            }}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td style={{ padding: "16px 20px" }}>
                          <span
                            style={{
                              padding: "3px 6px",
                              borderRadius: "4px",
                              background: "rgba(255,255,255,0.04)",
                              border: "1px solid var(--border)",
                              fontSize: "11.5px",
                              textTransform: "capitalize",
                              color: "var(--text)"
                            }}
                          >
                            {log.category}
                          </span>
                        </td>
                        <td style={{ padding: "16px 20px", fontWeight: "600", color: "var(--text)" }}>
                          {log.action_type}
                        </td>
                        <td style={{ padding: "16px 20px", color: "var(--text)" }}>
                          {log.description}
                        </td>
                      </tr>
                      {isExpanded && log.details && (
                        <tr style={{ background: "rgba(0, 0, 0, 0.2)" }}>
                          <td colSpan={5} style={{ padding: "20px", borderBottom: "1px solid var(--border)" }}>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Raw Event Details (JSON)</span>
                              <pre
                                style={{
                                  background: "rgba(255,255,255,0.02)",
                                  padding: "16px",
                                  borderRadius: "6px",
                                  border: "1px solid var(--border)",
                                  fontSize: "12.5px",
                                  color: "#a7f3d0",
                                  overflowX: "auto",
                                  whiteSpace: "pre-wrap",
                                  fontFamily: "monospace"
                                }}
                              >
                                {JSON.stringify(JSON.parse(log.details), null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </table>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * AURA OS Workspace Files Explorer
 * Interactive folder tree browser and high-fidelity text/code reader.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { FileNode, WorkspaceFileDetail } from "@/types";
import { Folder, FolderOpen, FileText, Code, Settings, Terminal, RefreshCw, X } from "lucide-react";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";
import { LiveSandbox } from "@/components/sandbox/LiveSandbox";

export function FilesPage() {
  const [tree, setTree] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<WorkspaceFileDetail | null>(null);
  const [reading, setReading] = useState(false);
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({ "": true }); // Root open by default
  const [isDeveloperMode, setIsDeveloperMode] = useState(false);
  const { showToast } = useNotification();

  const checkDevMode = useCallback(() => {
    const dev = localStorage.getItem("aura_developer_mode") === "true";
    setIsDeveloperMode(dev);
  }, []);

  const fetchTree = useCallback(async () => {
    setLoading(true);
    checkDevMode();
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_developer_token") || "";
      const resp = await fetchWithAuth(`${apiBase}/files`, {
        headers: {
          "X-Developer-Token": token
        }
      });
      if (resp.ok) {
        const data = await resp.json();
        setTree(data);
      } else {
        showToast("Failed to fetch workspace file tree", "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Error connecting to file service", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast, checkDevMode]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  const handleReadFile = async (path: string) => {
    setReading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_developer_token") || "";
      const resp = await fetchWithAuth(`${apiBase}/files/read?path=${encodeURIComponent(path)}`, {
        headers: {
          "X-Developer-Token": token
        }
      });
      if (resp.ok) {
        const data = await resp.json();
        setSelectedFile(data);
      } else {
        const err = await resp.json();
        showToast(err.detail || "Failed to load file", "error");
      }
    } catch (e) {
      console.error(e);
      showToast("Error loading file contents", "error");
    } finally {
      setReading(false);
    }
  };

  const toggleFolder = (path: string) => {
    setOpenFolders((prev) => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  // Render tree node recursive component
  const renderNode = (node: FileNode) => {
    const isDir = node.type === "directory";
    const path = node.path;
    const isOpen = openFolders[path];
    const depth = path ? path.split("/").length : 0;

    if (isDir) {
      return (
        <div key={path} style={{ display: "flex", flexDirection: "column" }}>
          <button
            onClick={() => toggleFolder(path)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 8px",
              paddingLeft: `${depth * 12 + 8}px`,
              background: "none",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
              textAlign: "left",
              fontSize: "13px",
              width: "100%",
              borderRadius: "6px",
              transition: "all var(--transition-fast)"
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.02)"}
            onMouseLeave={(e) => e.currentTarget.style.background = "none"}
          >
            <span style={{ color: "var(--accent-cyan)", display: "flex", alignItems: "center" }}>
              {isOpen ? <FolderOpen size={14} /> : <Folder size={14} />}
            </span>
            <span style={{ fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {node.name}
            </span>
          </button>
          
          {isOpen && node.children && (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {node.children.map((child) => renderNode(child))}
            </div>
          )}
        </div>
      );
    }

    return (
      <button
        key={path}
        onClick={() => handleReadFile(path)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 8px",
          paddingLeft: `${depth * 12 + 8}px`,
          background: selectedFile?.path === path ? "rgba(6, 214, 214, 0.05)" : "none",
          border: "none",
          color: selectedFile?.path === path ? "var(--text-primary)" : "var(--text-secondary)",
          cursor: "pointer",
          textAlign: "left",
          fontSize: "13px",
          width: "100%",
          borderRadius: "6px",
          transition: "all var(--transition-fast)"
        }}
        onMouseEnter={(e) => {
          if (selectedFile?.path !== path) {
            e.currentTarget.style.background = "rgba(255,255,255,0.02)";
          }
        }}
        onMouseLeave={(e) => {
          if (selectedFile?.path !== path) {
            e.currentTarget.style.background = "none";
          }
        }}
      >
        <span style={{ color: "var(--accent-purple)", display: "flex", alignItems: "center" }}>
          <FileText size={14} />
        </span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {node.name}
        </span>
      </button>
    );
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        width: "100%",
        overflow: "hidden",
        background: "rgba(6, 6, 12, 0.25)"
      }}
      className="files-page-container"
    >
      {/* Directory Explorer Pane */}
      <div
        style={{
          width: selectedFile ? "260px" : "100%",
          minWidth: "200px",
          borderRight: selectedFile ? "1px solid rgba(255,255,255,0.03)" : "none",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
          transition: "width 0.3s ease"
        }}
      >
        {/* Explorer Header */}
        <div
          style={{
            padding: "16px",
            borderBottom: "1px solid rgba(255,255,255,0.03)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", letterSpacing: "0.5px" }}>
              📂 FILES EXPLORER
            </span>
            <span style={{
              fontSize: "10px",
              fontWeight: "600",
              padding: "2px 8px",
              borderRadius: "12px",
              border: isDeveloperMode ? "1px solid rgba(248, 113, 113, 0.2)" : "1px solid rgba(6, 214, 214, 0.2)",
              color: isDeveloperMode ? "#f87171" : "var(--accent-cyan)",
              background: isDeveloperMode ? "rgba(248, 113, 113, 0.05)" : "rgba(6, 214, 214, 0.05)",
              letterSpacing: "0.3px",
              textTransform: "uppercase"
            }}>
              {isDeveloperMode ? "Developer Mode" : "User Sandbox"}
            </span>
          </div>
          <button
            onClick={fetchTree}
            disabled={loading}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center"
            }}
            title="Refresh files"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* File tree */}
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 8px" }}>
          {loading && !tree ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "40px", fontSize: "12px" }}>
              Scanning workspace directories...
            </div>
          ) : tree ? (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {tree.children?.map((node) => renderNode(node))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "40px", fontSize: "12px" }}>
              No files indexed.
            </div>
          )}
        </div>
      </div>

      {/* Editor/Code Viewer Pane */}
      
        {selectedFile && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              height: "100%",
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.2)"
            }}
          >
            {/* Header */}
            <div
              style={{
                padding: "12px 16px",
                borderBottom: "1px solid rgba(255,255,255,0.03)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "rgba(0, 0, 0, 0.4)"
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", overflow: "hidden", marginRight: "8px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {selectedFile.name}
                </span>
                <span style={{ fontSize: "10px", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {selectedFile.path}
                </span>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  padding: "4px"
                }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Code viewport */}
            <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
              {reading ? (
                <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "80px", fontSize: "13px" }}>
                  Loading file contents...
                </div>
              ) : (
                <LiveSandbox
                  name={selectedFile.name}
                  path={selectedFile.path}
                  content={selectedFile.content}
                  onChange={(newContent) => {
                    setSelectedFile(prev => prev ? { ...prev, content: newContent } : null);
                  }}
                />
              )}
            </div>
          </div>
        )}
      
    </div>
  );
}

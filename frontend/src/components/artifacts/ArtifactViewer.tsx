"use client";

import React, { useState, useEffect } from "react";
import { fetchWithAuth } from "@/lib/api";
import { LiveSandbox } from "@/components/sandbox/LiveSandbox";
import { Folder, ExternalLink, Code } from "lucide-react";

interface ArtifactViewerProps {
  artifact: any;
  onOpenWorkspace?: () => void;
}

export function ArtifactViewer({ artifact, onOpenWorkspace }: ArtifactViewerProps) {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadFiles = async () => {
      setLoading(true);
      setError(null);
      try {
        const fileData: Record<string, string> = {};
        for (const file of artifact.files) {
          const filePath = typeof file === "string" ? file : file.path;
          if (!filePath) continue;
          
          const pathParam = `Projects/${artifact.slug}/${filePath}`;
          const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
          const res = await fetchWithAuth(`${apiBase}/files/read?path=${encodeURIComponent(pathParam)}`);
          
          if (res.ok) {
            const data = await res.json();
            fileData[filePath] = data.content;
          } else {
            console.warn("Failed to fetch file:", filePath);
          }
        }
        if (isMounted) {
          setFiles(fileData);
          
          // Try to auto-select an entry point file for preview
          const defaultFile = artifact.files.find((f: any) => {
            const p = typeof f === "string" ? f : f.path;
            return p.endsWith(".html") || p.endsWith(".tsx") || p.endsWith(".jsx") || p.endsWith(".py") || p.endsWith(".js") || p.endsWith(".md");
          }) || artifact.files[0];
          
          if (defaultFile) {
            setActiveFile(typeof defaultFile === "string" ? defaultFile : defaultFile.path);
          }
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(String(err));
          setLoading(false);
        }
      }
    };
    
    if (artifact.slug && artifact.files && artifact.files.length > 0) {
      loadFiles();
    } else {
      setLoading(false);
      setError("Invalid artifact format");
    }
    
    return () => { isMounted = false; };
  }, [artifact]);

  if (loading) {
    return (
      <div style={{ padding: "16px", fontSize: "13px", color: "var(--accent-cyan)", border: "1px solid rgba(6, 214, 214, 0.2)", borderRadius: "12px", background: "rgba(6, 214, 214, 0.05)", marginTop: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
        <div className="animate-spin" style={{ width: "14px", height: "14px", border: "2px solid rgba(6, 214, 214, 0.2)", borderTopColor: "var(--accent-cyan)", borderRadius: "50%" }} />
        Loading Live Preview...
      </div>
    );
  }

  if (error) {
    return <div style={{ color: "var(--error)", padding: "12px", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "12px", marginTop: "12px" }}>Error loading preview: {error}</div>;
  }

  return (
    <div className="artifact-viewer" style={{
      border: "1px solid rgba(255, 255, 255, 0.1)",
      borderRadius: "12px",
      overflow: "hidden",
      background: "#050508",
      display: "flex",
      flexDirection: "column",
      height: "500px",
      marginTop: "12px",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)"
    }}>
      <div className="artifact-header" style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 16px",
        background: "rgba(255, 255, 255, 0.05)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.05)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--accent-cyan)", fontSize: "13px", fontWeight: 600 }}>
          <Code size={16} />
          {artifact.name || artifact.slug || "Artifact"}
        </div>
        {onOpenWorkspace && (
          <button
            onClick={onOpenWorkspace}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              fontSize: "11px",
              background: "rgba(6, 214, 214, 0.1)",
              border: "1px solid rgba(6, 214, 214, 0.2)",
              color: "var(--accent-cyan)",
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(6, 214, 214, 0.2)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(6, 214, 214, 0.1)"; }}
          >
            <ExternalLink size={12} />
            Open Workspace
          </button>
        )}
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {Object.keys(files).length > 1 && (
          <div style={{
            width: "180px",
            borderRight: "1px solid rgba(255,255,255,0.05)",
            background: "rgba(0,0,0,0.2)",
            overflowY: "auto",
            padding: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "2px"
          }}>
            <div style={{ fontSize: "10px", textTransform: "uppercase", color: "var(--text-muted)", padding: "4px 8px", marginBottom: "4px", fontWeight: 600 }}>
              Files
            </div>
            {Object.keys(files).map((f) => (
              <div
                key={f}
                onClick={() => setActiveFile(f)}
                style={{
                  padding: "6px 8px",
                  fontSize: "11px",
                  color: activeFile === f ? "var(--text-primary)" : "var(--text-muted)",
                  background: activeFile === f ? "rgba(255,255,255,0.05)" : "transparent",
                  cursor: "pointer",
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
              >
                <Folder size={12} color={activeFile === f ? "var(--accent-cyan)" : "currentColor"} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f}</span>
              </div>
            ))}
          </div>
        )}
        
        <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
          {activeFile && (
            <LiveSandbox
              name={activeFile}
              path={`Projects/${artifact.slug}/${activeFile}`}
              content={files[activeFile] || ""}
              onChange={(c) => setFiles(prev => ({...prev, [activeFile]: c}))}
              isTemporary={false}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * AURA OS Live Sandbox Component
 * Side-by-side code editor, compiler, HTML/React/Markdown preview, and interactive console feed.
 */

"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { Terminal, Save, Play, RefreshCw, Sparkles, AlertCircle, Eye, Code, Download, ExternalLink } from "lucide-react";

interface LiveSandboxProps {
  name: string;
  path: string;
  content: string;
  onChange: (newContent: string) => void;
  isTemporary?: boolean;
  onOpenInWorkspace?: () => void;
}

export function LiveSandbox({
  name,
  path,
  content,
  onChange,
  isTemporary = false,
  onOpenInWorkspace,
}: LiveSandboxProps) {
  const [saveStatus, setSaveStatus] = useState<"saved" | "saving" | "error" | "dirty" | null>("saved");
  const [consoleLogs, setConsoleLogs] = useState<{ type: "log" | "error" | "warn"; text: string }[]>([]);
  const [previewKey, setPreviewKey] = useState(0); // For forcing iframe refreshes
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");
  const [deployMessage, setDeployMessage] = useState<string | null>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const extension = useMemo(() => {
    const parts = name.split(".");
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
  }, [name]);

  // Clear console logs on file changes
  useEffect(() => {
    setConsoleLogs([]);
  }, [path]);

  // Debounced auto-save to backend
  useEffect(() => {
    if (isTemporary) return; // Do not auto-save temp files
    
    // Ignore first load trigger
    if (saveStatus === "saved") return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setSaveStatus("dirty");

    saveTimeoutRef.current = setTimeout(async () => {
      setSaveStatus("saving");
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const token = localStorage.getItem("aura_developer_token") || "";
        const resp = await fetch(`${apiBase}/files/write`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Developer-Token": token,
          },
          body: JSON.stringify({
            path: path,
            content: content,
          }),
        });

        if (resp.ok) {
          setSaveStatus("saved");
        } else {
          setSaveStatus("error");
        }
      } catch (err) {
        console.error("Auto save failed:", err);
        setSaveStatus("error");
      }
    }, 1000); // 1s debounce

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [content]);

  // Capture logging events sent from iframe sandbox
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && (e.data.type === "CONSOLE_LOG" || e.data.type === "CONSOLE_ERROR" || e.data.type === "CONSOLE_WARN")) {
        const typeMap = { CONSOLE_LOG: "log", CONSOLE_ERROR: "error", CONSOLE_WARN: "warn" } as const;
        setConsoleLogs((prev) => [
          ...prev,
          {
            type: typeMap[e.data.type as keyof typeof typeMap],
            text: e.data.data,
          },
        ]);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  // Transpile JSX and construct Sandboxed Iframe content
  const previewSrcDoc = useMemo(() => {
    if (extension === "html" || extension === "htm") {
      return `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
              body { margin: 0; padding: 16px; font-family: system-ui, sans-serif; background: #0b0b14; color: #f1f5f9; }
            </style>
          </head>
          <body>
            ${content}
          </body>
        </html>
      `;
    }

    if (["jsx", "tsx", "js", "ts"].includes(extension)) {
      // Remove ES6 import lines to run correctly in global script tags
      const cleanedCode = content
        .replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];?/g, "")
        .replace(/export\s+default\s+/g, "const App = ")
        .replace(/export\s+/g, "");

      return `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8" />
            <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
            <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
            <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
              body {
                margin: 0;
                padding: 20px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #0b0b14;
                color: #f1f5f9;
              }
              #root {
                width: 100%;
                height: 100%;
              }
            </style>
          </head>
          <body>
            <div id="root"></div>
            <script>
              const _log = console.log;
              const _error = console.error;
              const _warn = console.warn;
              
              window.addEventListener("error", (event) => {
                window.parent.postMessage({ type: "CONSOLE_ERROR", data: event.message }, "*");
              });

              console.log = (...args) => {
                window.parent.postMessage({ type: "CONSOLE_LOG", data: args.map(a => typeof a === "object" ? JSON.stringify(a) : String(a)).join(" ") }, "*");
                _log.apply(console, args);
              };
              console.error = (...args) => {
                window.parent.postMessage({ type: "CONSOLE_ERROR", data: args.map(a => typeof a === "object" ? JSON.stringify(a) : String(a)).join(" ") }, "*");
                _error.apply(console, args);
              };
              console.warn = (...args) => {
                window.parent.postMessage({ type: "CONSOLE_WARN", data: args.map(a => typeof a === "object" ? JSON.stringify(a) : String(a)).join(" ") }, "*");
                _warn.apply(console, args);
              };

              // Mock lucide-react icons so they don't throw ReferenceError when imports are stripped
              const lucideReactMock = new Proxy({}, {
                get: (target, prop) => {
                  return (props) => {
                    const size = props.size || 16;
                    const color = props.color || "currentColor";
                    return React.createElement(
                      "svg",
                      {
                        width: size,
                        height: size,
                        stroke: color,
                        fill: "none",
                        strokeWidth: 2,
                        strokeLinecap: "round",
                        strokeLinejoin: "round",
                        viewBox: "0 0 24 24",
                        className: props.className,
                        style: props.style
                      },
                      React.createElement("circle", { cx: 12, cy: 12, r: 4 })
                    );
                  };
                }
              });

              const commonIcons = [
                "Sparkles", "Save", "RefreshCw", "Play", "Terminal", "AlertCircle", "Copy", "Check", 
                "Folder", "FolderOpen", "FileText", "Code", "Settings", "Search", "User", "X", 
                "ArrowRight", "ArrowLeft", "Plus", "Minus", "Trash", "Edit", "LogOut", "Info", "RotateCcw",
                "Heart", "Star", "Home", "Settings2", "UserCheck", "Moon", "Sun", "Mail", "Lock", "Unlock", 
                "Eye", "EyeOff", "Menu", "ChevronDown", "ChevronUp", "ChevronRight", "ChevronLeft", 
                "CheckCircle", "AlertTriangle", "Clock", "Calendar", "Upload", "Download", "ExternalLink", 
                "Share2", "Bell", "Filter", "MoreHorizontal", "MoreVertical", "Book", "Database", "Cpu", 
                "Activity", "Layers", "Layout", "Grid", "List", "Hash", "Sliders", "Wrench", "Shield", 
                "Key", "Globe", "Cloud", "Link", "Send", "Paperclip"
              ];
              commonIcons.forEach(icon => {
                window[icon] = lucideReactMock[icon];
              });
            </script>
            <script type="text/babel">
              try {
                ${cleanedCode}
                
                const renderTarget = typeof App !== "undefined" ? App : null;
                if (renderTarget) {
                  const root = ReactDOM.createRoot(document.getElementById("root"));
                  root.render(React.createElement(renderTarget));
                } else {
                  const keys = Object.keys(window).filter(k => typeof window[k] === "function" && /^[A-Z]/.test(k));
                  if (keys.length > 0) {
                    const root = ReactDOM.createRoot(document.getElementById("root"));
                    root.render(React.createElement(window[keys[0]]));
                  } else {
                    document.getElementById("root").innerHTML = "<div class='text-sm text-yellow-500'>Write a React function component (e.g. export default function App()) to render live preview.</div>";
                  }
                }
              } catch (err) {
                window.parent.postMessage({ type: "CONSOLE_ERROR", data: err.toString() }, "*");
                document.getElementById("root").innerHTML = "<pre class='text-xs text-red-500 overflow-auto max-w-full white-space-pre-wrap'>" + err.toString() + "</pre>";
              }
            </script>
          </body>
        </html>
      `;
    }

    // Default: text/markdown preview fallback
    return "";
  }, [content, extension]);

  const cssSrcDoc = useMemo(() => {
    if (extension !== "css") return "";
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <style>${content}</style>
          <style>
            body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0b14; color: #f1f5f9; }
            .preview-container { display: flex; flex-direction: column; gap: 16px; max-width: 400px; margin: 0 auto; }
            .section-title { font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; }
            h1 { margin-top: 0; }
            button { padding: 8px 16px; border-radius: 6px; border: none; font-weight: 600; cursor: pointer; transition: all 0.2s; }
            .card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 16px; border-radius: 8px; }
            input { padding: 8px 12px; border-radius: 6px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); color: #fff; width: 100%; box-sizing: border-box; }
          </style>
        </head>
        <body>
          <div class="preview-container">
            <div>
              <div class="section-title">Headings</div>
              <h1>Heading 1 (h1)</h1>
              <h2>Heading 2 (h2)</h2>
              <h3>Heading 3 (h3)</h3>
            </div>
            <div>
              <div class="section-title">Buttons & Actions</div>
              <button class="btn btn-primary primary-btn button">Primary Button</button>
              <button class="btn btn-secondary secondary-btn button-secondary" style="margin-left: 8px;">Secondary Button</button>
            </div>
            <div>
              <div class="section-title">Text and Cards</div>
              <div class="card panel box">
                <p class="text paragraph" style="margin: 0;">This paragraph and card container are styled dynamically by your CSS rules.</p>
              </div>
            </div>
            <div>
              <div class="section-title">Inputs</div>
              <input type="text" class="input text-input field" placeholder="Enter text..." value="Styled Input Field" />
            </div>
          </div>
        </body>
      </html>
    `;
  }, [content, extension]);

  const handleManualSave = async () => {
    if (isTemporary) return;
    setSaveStatus("saving");
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_developer_token") || "";
      const resp = await fetch(`${apiBase}/files/write`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Developer-Token": token,
        },
        body: JSON.stringify({
          path: path,
          content: content,
        }),
      });

      if (resp.ok) {
        setSaveStatus("saved");
      } else {
        setSaveStatus("error");
      }
    } catch (err) {
      setSaveStatus("error");
    }
  };

  const getSlug = () => {
    if (!path) return "";
    const parts = path.split("Projects/");
    if (parts.length > 1) {
      return parts[1].split("/")[0];
    }
    return "";
  };

  const handleDownloadZip = () => {
    const slug = getSlug();
    if (!slug) return alert("No active project slug identified.");
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    window.open(`${apiBase}/projects/download?slug=${slug}`, "_blank");
  };

  const handleDeploy = () => {
    setDeployMessage("Deployment: Not performed. Vercel/Netlify integration requires configuration in .env.");
    setTimeout(() => {
      setDeployMessage(null);
    }, 4000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden" }}>
      {/* Sandbox Control Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          background: "rgba(0, 0, 0, 0.4)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.03)",
          fontSize: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>{name}</span>
          {!isTemporary && (
            <span
              style={{
                fontSize: "10px",
                color:
                  saveStatus === "saved"
                    ? "var(--success)"
                    : saveStatus === "saving"
                    ? "var(--accent-cyan)"
                    : saveStatus === "error"
                    ? "#ef4444"
                    : "#fbbf24",
              }}
            >
              {saveStatus === "saved"
                ? "✓ Saved"
                : saveStatus === "saving"
                ? "● Saving..."
                : saveStatus === "error"
                ? "✕ Save Error"
                : "● Unsaved changes"}
            </span>
          )}
        </div>

        {/* Tab Selection segments */}
        <div style={{ display: "flex", background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: "6px", padding: "2px" }}>
          <button
            onClick={() => setActiveTab("preview")}
            style={{
              background: activeTab === "preview" ? "rgba(255, 255, 255, 0.08)" : "transparent",
              border: "none",
              color: activeTab === "preview" ? "var(--text-primary)" : "var(--text-muted)",
              padding: "4px 10px",
              borderRadius: "4px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
            }}
          >
            <Eye size={11} />
            <span>Preview</span>
          </button>
          <button
            onClick={() => setActiveTab("code")}
            style={{
              background: activeTab === "code" ? "rgba(255, 255, 255, 0.08)" : "transparent",
              border: "none",
              color: activeTab === "code" ? "var(--text-primary)" : "var(--text-muted)",
              padding: "4px 10px",
              borderRadius: "4px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
            }}
          >
            <Code size={11} />
            <span>Code</span>
          </button>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {/* Download ZIP */}
          <button
            onClick={handleDownloadZip}
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.04)",
              color: "var(--text-secondary)",
              padding: "4px 8px",
              borderRadius: "6px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
            }}
            title="Download ZIP Archive"
          >
            <Download size={11} />
            <span>Download</span>
          </button>

          {/* Deploy */}
          <button
            onClick={handleDeploy}
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.04)",
              color: "var(--text-secondary)",
              padding: "4px 8px",
              borderRadius: "6px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "11px",
            }}
            title="Deploy Application"
          >
            <ExternalLink size={11} />
            <span>Deploy</span>
          </button>

          {activeTab === "preview" && (
            <button
              onClick={() => setPreviewKey((prev) => prev + 1)}
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.04)",
                color: "var(--text-secondary)",
                padding: "4px 8px",
                borderRadius: "6px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
              }}
              title="Reload Preview"
            >
              <RefreshCw size={11} />
              <span>Reload</span>
            </button>
          )}

          {activeTab === "code" && !isTemporary && (
            <button
              onClick={handleManualSave}
              disabled={saveStatus === "saved"}
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.04)",
                color: "var(--text-secondary)",
                padding: "4px 8px",
                borderRadius: "6px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
              }}
            >
              <Save size={11} />
              <span>Save</span>
            </button>
          )}
        </div>
      </div>

      {deployMessage && (
        <div style={{
          background: "rgba(239, 68, 68, 0.1)",
          borderBottom: "1px solid rgba(239, 68, 68, 0.2)",
          color: "#ef4444",
          fontSize: "11px",
          padding: "6px 16px",
          textAlign: "center",
          fontWeight: "500"
        }}>
          {deployMessage}
        </div>
      )}

      {/* Main Workspace Split layout */}
      <div style={{ flex: 1, display: "flex", width: "100%", overflow: "hidden" }}>
        {/* Left Side: Code Editor */}
        {activeTab === "code" && (
          <div
            style={{
              flex: 1,
              height: "100%",
              display: "flex",
              flexDirection: "column",
              background: "#050508",
            }}
          >
            <textarea
              value={content}
              onChange={(e) => {
                onChange(e.target.value);
                if (saveStatus === "saved") setSaveStatus("dirty");
              }}
              spellCheck={false}
              style={{
                flex: 1,
                width: "100%",
                height: "100%",
                background: "none",
                border: "none",
                outline: "none",
                resize: "none",
                padding: "16px",
                color: "#e2e8f0",
                fontFamily: "monospace",
                fontSize: "12.5px",
                lineHeight: "1.6",
                whiteSpace: "pre",
                overflow: "auto",
              }}
            />
          </div>
        )}

        {/* Right Side: Live Preview Pane */}
        {activeTab === "preview" && (
          <div style={{ flex: 1, height: "100%", display: "flex", flexDirection: "column", background: "#0b0b14" }}>
            {/* Preview Viewport */}
            <div style={{ flex: 1, width: "100%", overflow: "hidden", position: "relative" }}>
              {extension === "md" || extension === "markdown" ? (
                <MarkdownPreview content={content} />
              ) : extension === "json" ? (
                <JsonPreview content={content} />
              ) : extension === "css" ? (
                <iframe
                  key={previewKey}
                  srcDoc={cssSrcDoc}
                  title="CSS Visualizer"
                  style={{ width: "100%", height: "100%", border: "none", background: "#0b0b14" }}
                />
              ) : ["py", "python", "sh", "bash", "go", "rust", "cpp", "c", "java"].includes(extension) ? (
                <ScriptPreview content={content} extension={extension} />
              ) : extension === "sql" ? (
                <SqlPreview content={content} />
              ) : previewSrcDoc ? (
                <iframe
                  key={previewKey}
                  srcDoc={previewSrcDoc}
                  title="Live Sandbox Preview"
                  sandbox="allow-scripts"
                  style={{ width: "100%", height: "100%", border: "none", background: "#0b0b14" }}
                />
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", fontSize: "12.5px" }}>
                  Preview not supported for this file type
                </div>
              )}
            </div>

            {/* Interactive Console logs panel */}
            <div
              style={{
                height: "130px",
                borderTop: "1px solid rgba(255, 255, 255, 0.03)",
                background: "#08080f",
                display: "flex",
                flexDirection: "column",
                flexShrink: 0,
              }}
            >
              {/* Console Header */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "4px 12px",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.03)",
                  background: "rgba(0, 0, 0, 0.2)",
                }}
              >
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: "700",
                    color: "var(--text-secondary)",
                    letterSpacing: "1px",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Terminal size={10} />
                  CONSOLE OUTPUT
                </span>
                <button
                  onClick={() => setConsoleLogs([])}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "9px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Clear
                </button>
              </div>

              {/* Logs feed */}
              <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px", fontFamily: "monospace", fontSize: "11px", display: "flex", flexDirection: "column", gap: "4px" }}>
                {consoleLogs.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>Console clean. Trigger code execution to see logs...</div>
                ) : (
                  consoleLogs.map((log, idx) => (
                    <div
                      key={idx}
                      style={{
                        color: log.type === "error" ? "#f87171" : log.type === "warn" ? "#fbbf24" : "#cbd5e1",
                        display: "flex",
                        gap: "6px",
                        alignItems: "flex-start",
                        wordBreak: "break-all",
                      }}
                    >
                      <span>{log.type === "error" ? "✕" : log.type === "warn" ? "⚠" : "›"}</span>
                      <span>{log.text}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* Helper Visual Previewer Components */

function MarkdownPreview({ content }: { content: string }) {
  const parseMarkdown = (text: string) => {
    const lines = text.split("\n");
    const rendered: React.ReactNode[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.startsWith("# ")) {
        rendered.push(<h1 key={i} style={{ fontSize: "20px", fontWeight: "700", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "4px", margin: "16px 0 8px 0", color: "#f1f5f9" }}>{line.slice(2)}</h1>);
      } else if (line.startsWith("## ")) {
        rendered.push(<h2 key={i} style={{ fontSize: "17px", fontWeight: "700", margin: "14px 0 6px 0", color: "#f1f5f9" }}>{line.slice(3)}</h2>);
      } else if (line.startsWith("### ")) {
        rendered.push(<h3 key={i} style={{ fontSize: "14px", fontWeight: "700", margin: "12px 0 4px 0", color: "#cbd5e1" }}>{line.slice(4)}</h3>);
      } else if (line.startsWith("- ") || line.startsWith("* ")) {
        rendered.push(<li key={i} style={{ margin: "4px 0", color: "#cbd5e1", fontSize: "13px" }}>{line.slice(2)}</li>);
      } else if (line.startsWith("> ")) {
        rendered.push(
          <blockquote key={i} style={{ borderLeft: "3px solid var(--accent-cyan)", paddingLeft: "12px", color: "#94a3b8", fontStyle: "italic", margin: "8px 0" }}>
            {line.slice(2)}
          </blockquote>
        );
      } else if (line.trim() === "") {
        rendered.push(<div key={i} style={{ height: "8px" }} />);
      } else {
        rendered.push(<p key={i} style={{ margin: "6px 0", color: "#cbd5e1", fontSize: "13px", lineHeight: "1.6" }}>{line}</p>);
      }
    }
    return rendered;
  };

  return (
    <div style={{ padding: "20px", height: "100%", overflowY: "auto", background: "#0b0b14", scrollbarWidth: "thin" }}>
      {parseMarkdown(content)}
    </div>
  );
}

function JsonNode({ val, name, isLast }: { val: any; name: string; isLast: boolean }) {
  const [collapsed, setCollapsed] = useState(false);
  const type = typeof val;
  if (val === null) {
    return <div style={{ paddingLeft: "12px" }}><span style={{ color: "#a78bfa" }}>{name}:</span> <span style={{ color: "#cbd5e1" }}>null</span>{!isLast && ","}</div>;
  }
  if (type === "string") {
    return <div style={{ paddingLeft: "12px" }}><span style={{ color: "#818cf8" }}>{name}:</span> <span style={{ color: "#34d399" }}>"{val}"</span>{!isLast && ","}</div>;
  }
  if (type === "number" || type === "boolean") {
    return <div style={{ paddingLeft: "12px" }}><span style={{ color: "#818cf8" }}>{name}:</span> <span style={{ color: "#fbbf24" }}>{String(val)}</span>{!isLast && ","}</div>;
  }
  const isArray = Array.isArray(val);
  const keys = Object.keys(val);
  return (
    <div style={{ paddingLeft: "12px" }}>
      <span onClick={() => setCollapsed(!collapsed)} style={{ cursor: "pointer", color: "#818cf8", fontWeight: "600" }}>
        {collapsed ? "▶" : "▼"} {name}: {isArray ? "[" : "{"}
      </span>
      {!collapsed && (
        <div style={{ borderLeft: "1px solid rgba(255,255,255,0.05)", marginLeft: "6px" }}>
          {keys.map((k, idx) => (
            <JsonNode key={k} val={val[k]} name={isArray ? String(idx) : k} isLast={idx === keys.length - 1} />
          ))}
        </div>
      )}
      <span>{isArray ? "]" : "}"}{!isLast && ","}</span>
    </div>
  );
}

function JsonPreview({ content }: { content: string }) {
  try {
    const data = JSON.parse(content);
    return (
      <div style={{ padding: "16px", height: "100%", overflowY: "auto", fontFamily: "monospace", fontSize: "12px" }}>
        <JsonNode val={data} name="Root" isLast={true} />
      </div>
    );
  } catch (err: any) {
    return (
      <div style={{ padding: "16px", color: "#f87171" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", fontWeight: "600" }}>
          <AlertCircle size={16} />
          <span>Invalid JSON Syntax</span>
        </div>
        <pre style={{ fontSize: "11px", background: "rgba(239,68,68,0.05)", padding: "12px", borderRadius: "6px", border: "1px solid rgba(239,68,68,0.1)", whiteSpace: "pre-wrap" }}>{err.message}</pre>
      </div>
    );
  }
}

function ScriptPreview({ content, extension }: { content: string; extension: string }) {
  const [running, setRunning] = useState(false);
  const [terminalOutput, setTerminalOutput] = useState<{ type: string; text: string }[]>([]);

  const handleRun = async () => {
    setRunning(true);
    setTerminalOutput([
      { type: "system", text: `[system] Initializing virtual sandbox environment...` },
      { type: "system", text: `[system] Running compiler for target [${extension}]...` },
      { type: "system", text: "" }
    ]);
    
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("aura_access_token") || "";
      
      const response = await fetch(`${apiBase}/execution/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          lang: extension,
          code: content
        })
      });

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const block of lines) {
          if (block.startsWith("data: ")) {
            const dataStr = block.slice(6);
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.type === "done") {
                break;
              }
              setTerminalOutput(prev => [...prev, { type: parsed.type, text: parsed.data }]);
            } catch (e) {
              console.error("SSE parse error:", e);
            }
          }
        }
      }
      
      setTerminalOutput(prev => [...prev, { type: "system", text: "" }, { type: "system", text: "[process completed]" }]);
    } catch (err: any) {
      setTerminalOutput(prev => [...prev, { type: "error", text: `Error: ${err.message}` }]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ padding: "16px", height: "100%", overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px", background: "#06060a" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "8px" }}>
        <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>Secure Runtime Simulator</span>
        <button
          onClick={handleRun}
          disabled={running}
          style={{
            background: "rgba(52, 211, 153, 0.08)",
            border: "1px solid rgba(52, 211, 153, 0.2)",
            color: "#34d399",
            padding: "4px 10px",
            borderRadius: "6px",
            fontSize: "11px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontWeight: "600"
          }}
        >
          <Play size={10} />
          <span>{running ? "Executing..." : "Run Script"}</span>
        </button>
      </div>

      <div style={{ flex: 1, minHeight: "150px", background: "#020204", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.03)", padding: "12px", fontFamily: "monospace", fontSize: "12px", color: "#cbd5e1", display: "flex", flexDirection: "column", overflowY: "auto" }}>
        <div style={{ color: "#64748b", marginBottom: "8px" }}>admin@aura:~/sandbox$ {extension === "py" ? "python" : extension === "sh" ? "bash" : extension === "java" ? "java" : "./run"} script.{extension}</div>
        
        {terminalOutput.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
            {terminalOutput.map((line, i) => (
              <div key={i} style={{ 
                color: line.type === "system" ? "#64748b" : 
                       line.type === "error" ? "#f87171" : 
                       "#cbd5e1",
                whiteSpace: "pre-wrap"
              }}>{line.text}</div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#475569", fontStyle: "italic" }}>Click "Run Script" to execute and see console output...</div>
        )}
        
        {running && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }}>
            <span style={{ color: "#38bdf8" }}>⚡ Running...</span>
          </div>
        )}
      </div>
    </div>
  );
}

function SqlPreview({ content }: { content: string }) {
  const [queryRan, setQueryRan] = useState(false);
  const [running, setRunning] = useState(false);

  const tableMatch = content.match(/from\s+([a-zA-Z0-9_]+)/i);
  const tableName = tableMatch ? tableMatch[1] : "results";

  const handleRunQuery = () => {
    setRunning(true);
    setTimeout(() => {
      setRunning(false);
      setQueryRan(true);
    }, 800);
  };

  const getMockData = (tbl: string) => {
    const name = tbl.toLowerCase();
    if (name === "users" || name === "user" || name === "accounts") {
      return {
        columns: ["id", "username", "email", "role", "created_at"],
        rows: [
          ["1", "admin", "admin@aura.ai", "OWNER", "2026-06-01"],
          ["2", "deepmind_agent", "agent@deepmind.com", "ADMIN", "2026-06-20"],
          ["3", "developer", "dev@aura.ai", "DEVELOPER", "2026-06-21"]
        ]
      };
    }
    if (name === "logs" || name === "activities" || name === "audit") {
      return {
        columns: ["id", "timestamp", "severity", "message", "operator"],
        rows: [
          ["1001", "2026-06-21T02:15:00", "INFO", "Quantum link established", "system"],
          ["1002", "2026-06-21T02:16:30", "WARNING", "Provider switch: Gemini -> Groq", "manager"],
          ["1003", "2026-06-21T02:18:00", "INFO", "OAuth verification complete", "OWNER"]
        ]
      };
    }
    return {
      columns: ["id", "status", "hash", "timestamp"],
      rows: [
        ["1", "ACTIVE", "0x89fbc812", "2026-06-21"],
        ["2", "COMPLETED", "0xa38c71f9", "2026-06-21"],
        ["3", "PENDING", "0x39fa8c1a", "2026-06-21"]
      ]
    };
  };

  const data = getMockData(tableName);

  return (
    <div style={{ padding: "16px", height: "100%", overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px", background: "#06060a" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "8px" }}>
        <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>Database Query Simulator</span>
        <button
          onClick={handleRunQuery}
          disabled={running}
          style={{
            background: "rgba(6, 214, 214, 0.08)",
            border: "1px solid rgba(6, 214, 214, 0.2)",
            color: "var(--accent-cyan)",
            padding: "4px 10px",
            borderRadius: "6px",
            fontSize: "11px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontWeight: "600"
          }}
        >
          <Play size={10} />
          <span>{running ? "Executing..." : "Execute Query"}</span>
        </button>
      </div>

      <div style={{ flex: 1, minHeight: "150px", background: "#020204", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.03)", padding: "12px", display: "flex", flexDirection: "column" }}>
        {running ? (
          <div style={{ margin: "auto", color: "var(--accent-cyan)", fontSize: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
            <div className="tool-spinner" style={{ width: "12px", height: "12px", border: "2px solid rgba(6,214,214,0.1)", borderTopColor: "var(--accent-cyan)" }} />
            Evaluating query against local schema...
          </div>
        ) : queryRan ? (
          <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div style={{ fontSize: "11px", color: "#34d399", marginBottom: "8px", fontWeight: "600" }}>
              ✓ Success: 3 rows returned from table "{tableName}" (12ms)
            </div>
            <div style={{ flex: 1, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", fontFamily: "monospace", color: "#cbd5e1", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    {data.columns.map((c, i) => (
                      <th key={i} style={{ padding: "6px", color: "var(--accent-cyan)", fontWeight: "600" }}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, rIdx) => (
                    <tr key={rIdx} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                      {row.map((val, cIdx) => (
                        <td key={cIdx} style={{ padding: "6px" }}>{val}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={{ margin: "auto", color: "#475569", fontStyle: "italic", fontSize: "12px" }}>
            Click "Execute Query" to inspect simulated database output...
          </div>
        )}
      </div>
    </div>
  );
}


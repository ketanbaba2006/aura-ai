/**
 * AURA OS Chat Input
 * Futuristic floating glass pill composer with neon glow effects.
 */

"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Plus, Mic, ArrowUp, Square, Bot, Play, Pause } from "lucide-react";
import { useNotification } from "@/context/NotificationContext";
import type { ActiveView } from "@/types";
import { ActionMenu } from "./ActionMenu";
import { CameraCapture } from "./actions/CameraCapture";
import { AudioRecorder } from "./actions/AudioRecorder";
import { ImageEditor } from "./actions/ImageEditor";
import { PluginManager } from "./actions/PluginManager";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  isPaused?: boolean;
  onPauseToggle?: () => void;
  agentMode: boolean;
  onAgentModeChange: (enabled: boolean) => void;
  onSwitchView?: (view: ActiveView) => void;
  activeView?: string;
  conversationId?: string | null;
}

export function ChatInput({ 
  onSend, 
  onStop, 
  isStreaming, 
  isPaused = false,
  onPauseToggle,
  agentMode, 
  onAgentModeChange, 
  onSwitchView, 
  activeView, 
  conversationId 
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { showToast, showModal, closeModal } = useNotification();
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isActionMenuOpen, setIsActionMenuOpen] = useState(false);

  // Upload queue tracking
  interface UploadQueueItem {
    id: string;
    name: string;
    size: number;
    progress: number;
    status: "uploading" | "processing" | "completed" | "failed";
    error?: string;
  }
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);

  const CHUNK_SIZE = 4 * 1024 * 1024; // 4MB Slices

  const uploadFiles = async (files: FileList | File[] | File) => {
    const fileList = files instanceof File
      ? [files]
      : Array.isArray(files)
      ? files
      : Array.from(files);

    if (fileList.length === 0) return;
    setIsUploading(true);

    for (const file of fileList) {
      // Create locally unique identifier scoped by file metadata to enable resumable checks
      const storageKey = `aura_upload_session_${file.name}_${file.size}`;
      let uploadId = localStorage.getItem(storageKey);
      if (!uploadId) {
        uploadId = Math.random().toString(36).substring(2) + Date.now().toString(36);
        localStorage.setItem(storageKey, uploadId);
      }

      // Initialize queue state card
      const queueItem: UploadQueueItem = {
        id: uploadId,
        name: file.name,
        size: file.size,
        progress: 0,
        status: "uploading"
      };
      
      setUploadQueue(prev => {
        // Prevent duplicate queue card rendering
        if (prev.some(item => item.id === uploadId)) {
          return prev.map(item => item.id === uploadId ? { ...item, status: "uploading", error: undefined } : item);
        }
        return [...prev, queueItem];
      });

      // Fire asynchronous chunk upload loop
      runChunkedUpload(file, uploadId, storageKey);
    }
  };

  const runChunkedUpload = async (file: File, uploadId: string, storageKey: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    
    try {
      // 1. Inquire server to check if parts have been pre-uploaded (resumable connection recovery)
      let uploadedChunks: number[] = [];
      try {
        const statusResp = await fetch(`${apiBase}/knowledge/upload/status?upload_id=${uploadId}`);
        if (statusResp.ok) {
          const statusData = await statusResp.json();
          uploadedChunks = statusData.uploaded_chunks || [];
        }
      } catch (err) {
        console.warn("Failed retrieving upload session status, beginning fresh upload:", err);
      }

      let success = true;

      // 2. Loop slices
      for (let index = 0; index < totalChunks; index++) {
        if (uploadedChunks.includes(index)) {
          const currentProgress = Math.round(((index + 1) / totalChunks) * 100);
          setUploadQueue(prev =>
            prev.map(item => item.id === uploadId ? { ...item, progress: currentProgress } : item)
          );
          continue;
        }

        const start = index * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunkBlob = file.slice(start, end);

        // Populate chunked payload
        const formData = new FormData();
        formData.append("upload_id", uploadId);
        formData.append("chunk_index", index.toString());
        formData.append("total_chunks", totalChunks.toString());
        formData.append("filename", file.name);
        formData.append("file", chunkBlob, file.name);
        if (conversationId) {
          formData.append("conversation_id", conversationId);
        }

        // Chunk retry handler: max 3 attempts
        let retries = 3;
        let chunkSuccess = false;
        let lastError = "";

        while (retries > 0 && !chunkSuccess) {
          try {
            const resp = await fetch(`${apiBase}/knowledge/upload/chunk`, {
              method: "POST",
              body: formData,
            });
            if (resp.ok) {
              const data = await resp.json();
              chunkSuccess = true;
              
              const currentProgress = Math.round(((index + 1) / totalChunks) * 100);
              
              if (data.status === "completed") {
                // Compilation merge began on the server, update status to processing
                setUploadQueue(prev =>
                  prev.map(item => item.id === uploadId ? { ...item, progress: 100, status: "processing" } : item)
                );
                
                // Clear session storage pointer
                localStorage.removeItem(storageKey);
                
                // Start background indexing status poll loops
                pollProcessingStatus(data.id, uploadId, file.name);
              } else {
                setUploadQueue(prev =>
                  prev.map(item => item.id === uploadId ? { ...item, progress: currentProgress } : item)
                );
              }
            } else {
              retries--;
              lastError = `Server response code: ${resp.status}`;
              if (retries > 0) await new Promise(r => setTimeout(r, 1000));
            }
          } catch (err: any) {
            retries--;
            lastError = err.message || "Network request failed";
            if (retries > 0) await new Promise(r => setTimeout(r, 1500));
          }
        }

        if (!chunkSuccess) {
          success = false;
          throw new Error(lastError || "Chunk upload failure.");
        }
      }

    } catch (err: any) {
      setUploadQueue(prev =>
        prev.map(item => item.id === uploadId ? { ...item, status: "failed", error: err.message || "Upload interrupted" } : item)
      );
      showToast(`Upload failed for ${file.name}: ${err.message || ""}`, "error");
    } finally {
      setIsUploading(false);
    }
  };

  const pollProcessingStatus = async (docId: string, uploadId: string, filename: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    let attempts = 60; // Poll up to 10 minutes (10s intervals)
    
    const interval = setInterval(async () => {
      attempts--;
      try {
        const resp = await fetch(`${apiBase}/knowledge/documents`);
        if (resp.ok) {
          const docs = await resp.json();
          const doc = docs.find((d: any) => d.id === docId);
          if (doc) {
            if (doc.status === "completed") {
              clearInterval(interval);
              setUploadQueue(prev =>
                prev.map(item => item.id === uploadId ? { ...item, status: "completed" } : item)
              );
              showToast(`Indexed ${filename} into conversation context!`, "success");
              onSend(`Uploaded and indexed document: ${filename}`);
              
              // Clear progress indicator card after 4 seconds
              setTimeout(() => {
                setUploadQueue(prev => prev.filter(item => item.id !== uploadId));
              }, 4000);
            } else if (doc.status === "failed") {
              clearInterval(interval);
              setUploadQueue(prev =>
                prev.map(item => item.id === uploadId ? { ...item, status: "failed", error: doc.error_message || "Ingestion parsing failed" } : item)
              );
              showToast(`Failed to parse ${filename}`, "error");
            }
          }
        }
      } catch (e) {
        console.warn("Error checking processing telemetry:", e);
      }
      
      if (attempts <= 0) {
        clearInterval(interval);
        setUploadQueue(prev =>
          prev.map(item => item.id === uploadId ? { ...item, status: "failed", error: "Processing timeout." } : item)
        );
      }
    }, 10000);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      uploadFiles(e.target.files);
    }
  };

  // Keyboard shortcut listener to toggle menu (Cmd + / or Ctrl + /)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setIsActionMenuOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  // Inbound Paste files/text analyzer
  const handlePaste = useCallback(async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const filesToUpload: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          filesToUpload.push(file);
        }
      }
    }

    if (filesToUpload.length > 0) {
      e.preventDefault();
      uploadFiles(filesToUpload);
      showToast(`Ingesting clipboard payload...`, "info");
    }
  }, [uploadFiles, showToast]);

  // Execute clipboard read from Menu
  const handlePasteClipboard = async () => {
    try {
      const items = await navigator.clipboard.read();
      const filesToUpload: File[] = [];
      
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith("image/") || type.startsWith("video/") || type === "text/plain" || type === "application/pdf") {
            const blob = await item.getType(type);
            if (type === "text/plain") {
              const text = await blob.text();
              setInput(prev => prev + (prev ? " " : "") + text);
              showToast("Pasted clipboard text into chat composer", "success");
            } else {
              const ext = type.split("/")[1] || "file";
              const file = new File([blob], `clipboard_paste_${Date.now()}.${ext}`, { type });
              filesToUpload.push(file);
            }
          }
        }
      }

      if (filesToUpload.length > 0) {
        uploadFiles(filesToUpload);
        showToast(`Uploaded ${filesToUpload.length} clipboard file(s)`, "success");
      }
    } catch (err) {
      // Fallback to text reading if rich content permissions are blocked
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          setInput(prev => prev + (prev ? " " : "") + text);
          showToast("Pasted clipboard text into chat composer", "success");
        } else {
          showToast("Clipboard is empty", "info");
        }
      } catch (e) {
        showToast("Unable to read clipboard. Check site permissions.", "error");
      }
    }
  };

  // Switch execution pathways based on selected action
  const handleSelectAction = (actionId: string) => {
    setIsActionMenuOpen(false);

    switch (actionId) {
      case "upload_files":
        fileInputRef.current?.click();
        break;
      case "upload_images":
        imageInputRef.current?.click();
        break;
      case "upload_videos":
        videoInputRef.current?.click();
        break;
      case "upload_audio":
        audioInputRef.current?.click();
        break;
      case "upload_folder":
        folderInputRef.current?.click();
        break;
      case "upload_zip":
        zipInputRef.current?.click();
        break;
      case "paste_clipboard":
        handlePasteClipboard();
        break;
      case "capture_camera":
        showModal({
          title: "Camera Capture",
          description: "Authorize and capture device webcam snaps.",
          content: (
            <CameraCapture
              onCapture={(file) => {
                uploadFiles(file);
                closeModal();
              }}
              onClose={closeModal}
            />
          ),
          actions: [],
        });
        break;
      case "voice_recording":
        showModal({
          title: "Voice Notes Recorder",
          description: "Capture ambient audio waves directly.",
          content: (
            <AudioRecorder
              onRecord={(file) => {
                uploadFiles(file);
                closeModal();
              }}
              onClose={closeModal}
            />
          ),
          actions: [],
        });
        break;
      case "web_search":
        showToast("Web Search migrated to AURA OS v2.", "info");
        break;
      case "deep_research":
        setInput("/deep-search ");
        textareaRef.current?.focus();
        showToast("Deep Research mode selected. Input query topic.", "info");
        break;
      case "knowledge_search":
        showToast("Knowledge Search migrated to AURA OS v2.", "info");
        break;
      case "memory_search":
        showToast("Memory Search migrated to AURA OS v2.", "info");
        break;
      case "generate_image":
        setInput("/image ");
        textareaRef.current?.focus();
        showToast("Enter image details to prompt model", "info");
        break;
      case "edit_image":
        showModal({
          title: "Canvas Paint Editor",
          description: "Drag and drop or select images to paint annotations.",
          content: (
            <ImageEditor
              onSave={(file) => {
                uploadFiles(file);
                closeModal();
              }}
              onClose={closeModal}
            />
          ),
          actions: [],
        });
        break;
      case "code_interpreter":
        setInput("execute python:\n```python\n# Write your code here\n\n```");
        textareaRef.current?.focus();
        break;
      case "data_analysis":
        fileInputRef.current?.click();
        setInput("Analyze this dataset and generate key insights.");
        break;
      case "document_analysis":
        fileInputRef.current?.click();
        showToast("Document Analysis migrated to AURA OS v2.", "info");
        break;
      case "agent_mode":
        onAgentModeChange(!agentMode);
        showToast(`Agent Mode toggled ${!agentMode ? "ON" : "OFF"}`, "info");
        break;
      case "planner":
        showToast("Planner migrated to AURA OS v2.", "info");
        break;
      case "workspace":
        showToast("Workspace migrated to Builder mode.", "info");
        break;
      case "browser":
        showToast("Browser Panel migrated to AURA OS v2.", "info");
        break;
      case "plugins":
        showModal({
          title: "AURA Plugin Integrations",
          description: "Browse tool manager plugin configuration.",
          content: <PluginManager onClose={closeModal} />,
          actions: [],
        });
        break;
      case "developer_tools":
        showToast("Developer Tools migrated to AURA OS v2.", "info");
        break;
      default:
        console.warn("Unmapped action selection:", actionId);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  }, [onSend]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // Focus on mount and when streaming completes
  useEffect(() => {
    if (!isStreaming) {
      // Small delay to ensure DOM is ready and any animations complete
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [isStreaming]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [input, isStreaming, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const hasText = input.trim().length > 0;

  return (
    <div
      className="input-area"
      style={{
        padding: "0 24px 24px 24px",
        position: "relative",
        zIndex: 10,
        background: "var(--bg-void)",
      }}
    >
      <div className="input-wrapper" style={{ maxWidth: "768px", margin: "0 auto", position: "relative" }}>

        {/* Active Uploads Progress Tray */}
        {uploadQueue.length > 0 && (
          <div
            style={{
              position: "absolute",
              bottom: "calc(100% + 12px)",
              left: "14px",
              right: "14px",
              background: "linear-gradient(135deg, rgba(10, 10, 18, 0.98), rgba(10, 10, 18, 0.92))",
              backdropFilter: "blur(30px)",
              WebkitBackdropFilter: "blur(30px)",
              border: "1px solid rgba(6, 214, 214, 0.2)",
              borderRadius: "20px",
              padding: "16px 18px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              maxHeight: "180px",
              overflowY: "auto",
              overflowX: "hidden",
              zIndex: 100,
              boxShadow: "var(--shadow-lg)",
              transformStyle: "preserve-3d"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", fontWeight: "800", color: "var(--accent-cyan)", letterSpacing: "2px", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "6px" }}>
                <div
                >
                  🌀
                </div>
                Active File Ingestion Queue
              </span>
              <button
                onClick={() => setUploadQueue([])}
                style={{ background: "none", border: "1px solid rgba(255,255,255,0.1)", color: "var(--text-muted)", fontSize: "10px", cursor: "pointer", padding: "4px 10px", borderRadius: "8px" }}
              >
                Clear Queue
              </button>
            </div>
            {uploadQueue.map(item => (
              <div
                key={item.id}
                style={{ display: "flex", flexDirection: "column", gap: "6px", padding: "8px 10px", background: "rgba(255,255,255,0.02)", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px" }}>
                  <span style={{ color: "#fff", fontWeight: "500", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>
                    📄 {item.name} <span style={{ color: "var(--text-muted)", fontSize: "10px" }}>({(item.size / 1024 / 1024).toFixed(1)} MB)</span>
                  </span>
                  <span style={{
                    color: item.status === "completed" ? "var(--success)" : item.status === "failed" ? "var(--error)" : "var(--accent-cyan)",
                    fontWeight: "600",
                    fontSize: "11px"
                  }}>
                    {item.status === "uploading" ? `Uploading ${item.progress}%` :
                     item.status === "processing" ? "Processing (OCR/Index)..." :
                     item.status === "completed" ? "Completed" : "Failed"}
                  </span>
                </div>
                {/* Progress bar */}
                <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.04)", borderRadius: "3px", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${item.progress}%`,
                      height: "100%",
                      background: item.status === "completed" ? "var(--success)" : item.status === "failed" ? "var(--error)" : "var(--accent-primary)",
                      backgroundSize: "200% 200%",
                      animation: item.status === "uploading" ? "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite" : "none",
                      borderRadius: "3px"
                    }}
                  />
                </div>
                {item.error && (
                  <span style={{ color: "var(--error)", fontSize: "10px", marginTop: "4px" }}>
                    Error: {item.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: "10px",
            borderRadius: "32px",
            padding: "10px 12px 10px 16px",
            border: "1px solid",
            borderColor: isFocused ? "var(--text-muted)" : "var(--surface-border)",
            background: "var(--bg-elevated)",
            boxShadow: isFocused ? "0 0 15px rgba(255,255,255,0.05)" : "none",
            transition: "all 0.3s ease",
            transformStyle: "preserve-3d"
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
        >
          {/* Multiple File/Folder/ZIP Inputs */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept="*"
            style={{ display: "none" }}
          />
          <input
            type="file"
            ref={imageInputRef}
            onChange={handleFileChange}
            multiple
            accept="image/*"
            style={{ display: "none" }}
          />
          <input
            type="file"
            ref={videoInputRef}
            onChange={handleFileChange}
            multiple
            accept="video/*"
            style={{ display: "none" }}
          />
          <input
            type="file"
            ref={audioInputRef}
            onChange={handleFileChange}
            multiple
            accept="audio/*"
            style={{ display: "none" }}
          />
          <input
            type="file"
            ref={folderInputRef}
            onChange={handleFileChange}
            {...({ webkitdirectory: "", directory: "", multiple: true } as any)}
            style={{ display: "none" }}
          />
          <input
            type="file"
            ref={zipInputRef}
            onChange={handleFileChange}
            accept=".zip"
            style={{ display: "none" }}
          />

          {/* Action Menu Trigger (+ Button) */}
          <button
            type="button"
            onClick={() => setIsActionMenuOpen(!isActionMenuOpen)}
            style={{
              background: "transparent",
              border: "none",
              color: isActionMenuOpen ? "var(--error)" : "var(--text-muted)",
              cursor: "pointer",
              padding: "8px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all var(--transition-normal)",
              outline: "none",
            }}
            title="Universal action menu"
          >
            <Plus size={20} />
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onPaste={handlePaste}
            placeholder="Message AURA..."
            rows={1}
            disabled={isStreaming}
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontFamily: "inherit",
              fontSize: "14px",
              lineHeight: "1.5",
              resize: "none",
              maxHeight: "150px",
              minHeight: "24px",
              padding: "6px 0",
            }}
          />

          {/* Mic */}
          <button
            onClick={() => handleSelectAction("voice_recording")}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "8px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all var(--transition-fast)",
              outline: "none",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--text-primary)";
              e.currentTarget.style.background = "var(--surface-glass-hover)";
              e.currentTarget.style.borderColor = "var(--surface-border-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-muted)";
              e.currentTarget.style.background = "transparent";
            }}
            title="Voice input"
          >
            <Mic size={18} />
          </button>

          {/* Send / Stop */}
          {isStreaming ? (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              {onPauseToggle && (
                <button
                  onClick={onPauseToggle}
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))",
                    border: "1px solid rgba(255,255,255,0.12)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--text-primary)",
                    flexShrink: 0,
                    outline: "none",
                    boxShadow: "0 0 10px rgba(0,0,0,0.3)"
                  }}
                  title={isPaused ? "Resume generating" : "Pause generating"}
                >
                  {isPaused ? (
                    <Play size={12} fill="var(--text-primary)" style={{ marginLeft: "1.5px" }} />
                  ) : (
                    <Pause size={12} fill="var(--text-primary)" />
                  )}
                </button>
              )}
              <button
                onClick={onStop}
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #ef4444, #dc2626)",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  flexShrink: 0,
                  outline: "none",
                }}
                title="Stop generating"
              >
                <Square size={12} fill="#fff" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleSend}
              disabled={!hasText}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                border: "none",
                cursor: hasText ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: hasText ? "var(--bg-primary)" : "var(--text-muted)",
                flexShrink: 0,
                outline: "none",
                background: hasText ? "var(--text-primary)" : "rgba(255, 255, 255, 0.05)",
                transition: "background 0.2s ease",
              }}
              title="Send"
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "transform 0.2s ease",
                }}
              >
                <ArrowUp size={18} strokeWidth={2.5} />
              </div>
            </button>
          )}
        </div>

        <div
          style={{
            textAlign: "center",
            marginTop: "10px",
            fontSize: "10px",
            color: "var(--text-muted)",
            opacity: 0.6,
          }}
        >
          AURA AI can make mistakes. Cross-check critical details.
        </div>

        {/* Action Menu Popover */}
        
          {isActionMenuOpen && (
            <ActionMenu
              isOpen={isActionMenuOpen}
              onClose={() => setIsActionMenuOpen(false)}
              onSelectAction={handleSelectAction}
              activeView={activeView || "chat"}
              agentMode={agentMode}
              inputContent={input}
            />
          )}
        
      </div>
    </div>
  );
}

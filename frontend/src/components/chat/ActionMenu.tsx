"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  File,
  Image,
  Video,
  Music,
  FolderOpen,
  Archive,
  Clipboard,
  Camera,
  Mic,
  Globe,
  Search,
  Sparkles,
  Paintbrush,
  Code,
  BarChart,
  FileText,
  Cpu,
  Database,
  Bot,
  Calendar,
  Briefcase,
  Brain,
  Tv,
  Puzzle,
  Settings,
  X
} from "lucide-react";

export type ActionCategory = "All" | "Files & Media" | "Input & Capture" | "Search & Knowledge" | "AI Capabilities" | "System & Core";

export interface ActionItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  category: ActionCategory;
  desc: string;
  shortcut?: string;
}

interface ActionMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAction: (actionId: string) => void;
  activeView: string;
  agentMode: boolean;
  inputContent: string;
}

export function ActionMenu({
  isOpen,
  onClose,
  onSelectAction,
  activeView,
  agentMode,
  inputContent
}: ActionMenuProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<ActionCategory>("All");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const filterInputRef = useRef<HTMLInputElement>(null);
  const listContainerRef = useRef<HTMLDivElement>(null);

  // Check viewport responsiveness
  useEffect(() => {
    const checkViewport = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkViewport();
    window.addEventListener("resize", checkViewport);
    return () => window.removeEventListener("resize", checkViewport);
  }, []);

  // Autofocus search on open
  useEffect(() => {
    if (isOpen) {
      setSearchQuery("");
      setHighlightedIndex(0);
      setTimeout(() => {
        filterInputRef.current?.focus();
      }, 80);
    }
  }, [isOpen]);

  const actions: ActionItem[] = useMemo(() => [
    { id: "upload_files", icon: <File size={16} />, label: "Upload Files", category: "Files & Media", desc: "Ingest document, text, or database files", shortcut: "F" },
    { id: "upload_images", icon: <Image size={16} />, label: "Upload Images", category: "Files & Media", desc: "Ingest PNG, JPG, or WebP images", shortcut: "I" },
    { id: "upload_videos", icon: <Video size={16} />, label: "Upload Videos", category: "Files & Media", desc: "Ingest MP4, MOV, or WEBM clips", shortcut: "V" },
    { id: "upload_audio", icon: <Music size={16} />, label: "Upload Audio", category: "Files & Media", desc: "Ingest WAV, MP3, or M4A files", shortcut: "U" },
    { id: "upload_folder", icon: <FolderOpen size={16} />, label: "Upload Folder", category: "Files & Media", desc: "Upload an entire file directory", shortcut: "O" },
    { id: "upload_zip", icon: <Archive size={16} />, label: "Upload ZIP Project", category: "Files & Media", desc: "Ingest zipped workspace packages", shortcut: "Z" },
    
    { id: "paste_clipboard", icon: <Clipboard size={16} />, label: "Paste Clipboard", category: "Input & Capture", desc: "Read text or files from clipboard", shortcut: "P" },
    { id: "capture_camera", icon: <Camera size={16} />, label: "Capture from Camera", category: "Input & Capture", desc: "Take a picture using device webcam", shortcut: "C" },
    { id: "voice_recording", icon: <Mic size={16} />, label: "Voice Recording", category: "Input & Capture", desc: "Record microphone voice notes", shortcut: "R" },
    
    { id: "web_search", icon: <Globe size={16} />, label: "Web Search", category: "Search & Knowledge", desc: "Search the live web using AURA browser", shortcut: "W" },
    { id: "deep_research", icon: <Search size={16} />, label: "Deep Research", category: "Search & Knowledge", desc: "Execute intensive, multi-step search loops", shortcut: "D" },
    { id: "knowledge_search", icon: <Cpu size={16} />, label: "Knowledge Search", category: "Search & Knowledge", desc: "Query vectors and index knowledge graphs", shortcut: "K" },
    { id: "memory_search", icon: <Database size={16} />, label: "Memory Search", category: "Search & Knowledge", desc: "Browse semantic conversation logs", shortcut: "M" },
    
    { id: "generate_image", icon: <Sparkles size={16} />, label: "Generate Image", category: "AI Capabilities", desc: "Create custom AI images from prompt text", shortcut: "G" },
    { id: "edit_image", icon: <Paintbrush size={16} />, label: "Edit Image", category: "AI Capabilities", desc: "Paint and draw modifications on images", shortcut: "E" },
    { id: "code_interpreter", icon: <Code size={16} />, label: "Code Interpreter", category: "AI Capabilities", desc: "Run Python computations in isolated sandbox", shortcut: "X" },
    { id: "data_analysis", icon: <BarChart size={16} />, label: "Data Analysis", category: "AI Capabilities", desc: "Ingest datasets to build graphs & insights", shortcut: "Y" },
    { id: "document_analysis", icon: <FileText size={16} />, label: "Document Analysis", category: "AI Capabilities", desc: "Extract context and summaries from PDFs", shortcut: "L" },
    
    { id: "agent_mode", icon: <Bot size={16} />, label: `Agent Mode (${agentMode ? 'On' : 'Off'})`, category: "System & Core", desc: "Toggle autonomous problem-solving mode", shortcut: "A" },
    { id: "memory", icon: <Brain size={16} />, label: "Memory Graph", category: "System & Core", desc: "View AI contextual associations", shortcut: "G" },
    { id: "browser", icon: <Tv size={16} />, label: "Browser Panel", category: "System & Core", desc: "Inspect chromium automated browser session", shortcut: "B" },
    { id: "plugins", icon: <Puzzle size={16} />, label: "Plugins Config", category: "System & Core", desc: "Configure tool plugins and API endpoints", shortcut: "T" },
    { id: "developer_tools", icon: <Settings size={16} />, label: "Developer Tools", category: "System & Core", desc: "Inspect execution sandboxes & activity logs", shortcut: "H" }
  ], [agentMode]);

  // Context-Aware Highlight ordering: moves highly relevant items to the top if context matches
  const contextAwareActions = useMemo(() => {
    let list = [...actions];

    // Context conditions
    const hasImageInChat = inputContent.toLowerCase().includes(".png") || inputContent.toLowerCase().includes(".jpg");
    const hasDataKeyword = inputContent.toLowerCase().includes("csv") || inputContent.toLowerCase().includes("json") || inputContent.toLowerCase().includes("data");

    if (hasImageInChat) {
      // Prioritize image editing & analysis
      list = list.sort((a, b) => {
        if (a.id === "edit_image") return -1;
        if (b.id === "edit_image") return 1;
        return 0;
      });
    } else if (hasDataKeyword) {
      // Prioritize data analysis
      list = list.sort((a, b) => {
        if (a.id === "data_analysis") return -1;
        if (b.id === "data_analysis") return 1;
        return 0;
      });
    }



    return list;
  }, [actions, inputContent, activeView]);

  // Apply search query & category tab filtering
  const filteredActions = useMemo(() => {
    return contextAwareActions.filter((act) => {
      const matchSearch =
        act.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        act.desc.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchCategory = selectedCategory === "All" || act.category === selectedCategory;

      return matchSearch && matchCategory;
    });
  }, [contextAwareActions, searchQuery, selectedCategory]);

  // Keep selection index bounded
  useEffect(() => {
    if (highlightedIndex >= filteredActions.length) {
      setHighlightedIndex(Math.max(0, filteredActions.length - 1));
    }
  }, [filteredActions, highlightedIndex]);

  // Keyboard navigation & search hooks
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape closes
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      // Grid/List movement
      const itemsCount = filteredActions.length;
      if (itemsCount === 0) return;

      const cols = isMobile ? 1 : 2; // 2 column grid on desktop

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + cols < itemsCount ? prev + cols : prev % cols));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev - cols >= 0 ? prev - cols : (Math.floor((itemsCount - 1) / cols) * cols) + (prev % cols)));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + 1 < itemsCount ? prev + 1 : 0));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : itemsCount - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredActions[highlightedIndex]) {
          onSelectAction(filteredActions[highlightedIndex].id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredActions, highlightedIndex, onClose, onSelectAction, isMobile]);

  // Scroll active item into view
  useEffect(() => {
    const list = listContainerRef.current;
    if (!list) return;
    const activeEl = list.querySelector("[data-highlighted='true']");
    if (activeEl) {
      activeEl.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex]);

  // Handle category clicks
  const selectCat = (cat: ActionCategory) => {
    setSelectedCategory(cat);
    setHighlightedIndex(0);
    filterInputRef.current?.focus();
  };

  const categoriesList: ActionCategory[] = [
    "All",
    "Files & Media",
    "Input & Capture",
    "Search & Knowledge",
    "AI Capabilities",
    "System & Core"
  ];

  if (!isOpen) return null;

  // GPU Animation styles
  const overlayAnimation: any = isMobile
    ? {
        initial: { y: "100%", opacity: 0 },
        animate: { y: 0, opacity: 1 },
        exit: { y: "100%", opacity: 0 },
        transition: { type: "spring", stiffness: 350, damping: 30 }
      }
    : {
        initial: { opacity: 0, scale: 0.95, y: 15 },
        animate: { opacity: 1, scale: 1, y: 0 },
        exit: { opacity: 0, scale: 0.95, y: 15 },
        transition: { duration: 0.15, ease: "easeOut" }
      };

  return (
    <>
      {/* Backdrop (mobile-focused or clicking outside closing) */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 900,
          background: isMobile ? "rgba(0, 0, 0, 0.5)" : "transparent",
          backdropFilter: isMobile ? "blur(4px)" : "none",
        }}
      />

      <div
        {...overlayAnimation}
        style={{
          position: isMobile ? "fixed" : "absolute",
          bottom: isMobile ? 0 : "calc(100% + 12px)",
          left: isMobile ? 0 : "0",
          right: isMobile ? 0 : "0",
          width: isMobile ? "100%" : "auto",
          height: isMobile ? "75vh" : "400px",
          background: "rgba(10, 10, 18, 0.88)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderRadius: isMobile ? "24px 24px 0 0" : "20px",
          border: isMobile ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255, 255, 255, 0.05)",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6), 0 0 32px rgba(6, 214, 214, 0.05)",
          display: "flex",
          flexDirection: "column",
          zIndex: 1000,
          overflow: "hidden",
          willChange: "transform, opacity"
        }}
      >
        {/* Search header bar */}
        <div
          style={{
            padding: "14px 18px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            flexShrink: 0,
          }}
        >
          <Search size={16} style={{ color: "var(--text-muted)" }} />
          <input
            ref={filterInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setHighlightedIndex(0);
            }}
            placeholder="Type search queries, or filter capabilities..."
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: "13.5px",
              padding: "2px 0",
            }}
          />
          {isMobile && (
            <button
              onClick={onClose}
              style={{ background: "none", border: "none", color: "var(--text-muted)" }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Master panels */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          
          {/* Categories Sidebar (hidden or scrollbar style on mobile) */}
          {!isMobile && (
            <div
              style={{
                width: "180px",
                borderRight: "1px solid rgba(255, 255, 255, 0.04)",
                display: "flex",
                flexDirection: "column",
                padding: "10px",
                gap: "3px",
                overflowY: "auto",
                background: "rgba(0, 0, 0, 0.15)",
              }}
            >
              {categoriesList.map((cat) => {
                const isActive = selectedCategory === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => selectCat(cat)}
                    style={{
                      textAlign: "left",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      fontSize: "11.5px",
                      fontWeight: isActive ? "600" : "500",
                      background: isActive ? "rgba(6, 214, 214, 0.05)" : "none",
                      border: "none",
                      color: isActive ? "var(--accent-cyan)" : "var(--text-secondary)",
                      cursor: "pointer",
                      transition: "all var(--transition-fast)",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.color = "var(--text-primary)";
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.color = "var(--text-secondary)";
                    }}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          )}

          {/* Grid Panel items */}
          <div
            ref={listContainerRef}
            style={{
              flex: 1,
              padding: "16px",
              overflowY: "auto",
              display: "grid",
              gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
              gridAutoRows: "max-content",
              gap: "8px",
            }}
          >
            {isMobile && (
              /* Mobile Category filter slider header */
              <div
                style={{
                  gridColumn: "1 / -1",
                  display: "flex",
                  gap: "6px",
                  overflowX: "auto",
                  paddingBottom: "10px",
                  borderBottom: "1px solid rgba(255,255,255,0.03)",
                  marginBottom: "8px",
                  scrollbarWidth: "none",
                }}
              >
                {categoriesList.map((cat) => {
                  const isActive = selectedCategory === cat;
                  return (
                    <button
                      key={cat}
                      onClick={() => selectCat(cat)}
                      style={{
                        whiteSpace: "nowrap",
                        padding: "5px 12px",
                        borderRadius: "999px",
                        fontSize: "11px",
                        fontWeight: "600",
                        background: isActive ? "var(--accent-cyan)" : "rgba(255, 255, 255, 0.03)",
                        border: "none",
                        color: isActive ? "#000" : "var(--text-secondary)",
                      }}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>
            )}

            {filteredActions.length === 0 ? (
              <div
                style={{ gridColumn: "1 / -1", textAlign: "center", color: "var(--text-muted)", padding: "40px 0", fontSize: "12px" }}
              >
                No operations match selection.
              </div>
            ) : (
              filteredActions.map((act, index) => {
                const isHighlighted = index === highlightedIndex;
                return (
                  <div
                    key={act.id}
                    data-highlighted={isHighlighted ? "true" : "false"}
                    onClick={() => onSelectAction(act.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px 16px",
                      borderRadius: "12px",
                      background: isHighlighted 
                        ? "linear-gradient(135deg, rgba(6, 214, 214, 0.12), rgba(139, 92, 246, 0.12))" 
                        : "rgba(255, 255, 255, 0.015)",
                      border: isHighlighted
                        ? "1px solid rgba(6, 214, 214, 0.3)"
                        : "1px solid rgba(255, 255, 255, 0.05)",
                      cursor: "pointer",
                      transformStyle: "preserve-3d"
                    }}
                    onMouseEnter={() => setHighlightedIndex(index)}
                  >
                    {/* Action Icon */}
                    <div
                      style={{
                        padding: "10px",
                        borderRadius: "10px",
                        background: isHighlighted 
                          ? "linear-gradient(135deg, rgba(6, 214, 214, 0.2), rgba(139, 92, 246, 0.2))" 
                          : "rgba(255, 255, 255, 0.03)",
                        color: isHighlighted ? "var(--accent-cyan)" : "var(--text-secondary)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: isHighlighted ? "0 0 15px rgba(6, 214, 214, 0.2)" : "none"
                      }}
                    >
                      {act.icon}
                    </div>

                    {/* Meta info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "13px", fontWeight: "700", color: "#fff" }}>
                          {act.label}
                        </span>
                        {!isMobile && act.shortcut && (
                          <span style={{ fontSize: "9px", color: "var(--text-muted)", padding: "2px 6px", background: "rgba(255,255,255,0.05)", borderRadius: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
                            {act.shortcut}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "3px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {act.desc}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Hotkeys footer bar */}
        {!isMobile && (
          <div
            style={{
              padding: "10px 18px",
              borderTop: "1px solid rgba(255, 255, 255, 0.04)",
              background: "rgba(0,0,0,0.2)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "10px",
              color: "var(--text-muted)",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", gap: "14px" }}>
              <span>↑↓←→ Navigate</span>
              <span>↵ Select</span>
              <span>Esc Close</span>
            </div>
            <span>AURA OS Universal Action Palette</span>
          </div>
        )}
      </div>
    </>
  );
}

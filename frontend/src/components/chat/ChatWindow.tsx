/**
 * AURA OS Chat Window
 * Futuristic message display with glass welcome cards and smooth scrolling.
 */

"use client";

import { useEffect, useRef, useCallback } from "react";
import type { AgentProgress, Message, ToolUsage } from "@/types";
import { MessageBubble } from "./MessageBubble";
import { AuraCore } from "../3d/AuraCore";
import { Search, FileText, Code, GraduationCap, Compass } from "lucide-react";
import { FloatingCard } from "./FloatingCard";
import { AuraThinkingState } from "./AuraThinkingState";
import { HomePage } from "../pages/HomePage";
import { AgentExecutionTracker } from "../agent/AgentExecutionTracker";
import type { ActiveView } from "@/types";

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  toolUsages: ToolUsage[];
  searchStatus: string | null;
  agentProgress: AgentProgress[];
  onSendHint: (hint: string) => void;
  onOpenArtifact?: (title: string, content: string, language?: string) => void;
  onRegenerate?: (messageId: string) => void;
  projectsList?: any[];
  onSwitchProject?: (id: string) => void;
  activeView?: ActiveView;
}

export function ChatWindow({
  messages,
  isStreaming,
  toolUsages,
  searchStatus,
  agentProgress,
  onSendHint,
  onOpenArtifact,
  onRegenerate,
  projectsList = [],
  onSwitchProject,
  activeView,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior });
    }
  }, []);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const threshold = 120;
    isNearBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.addEventListener("scroll", handleScroll, { passive: true });
      return () => el.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll]);

  const messagesCount = messages.length;
  useEffect(() => {
    // When a new message is added, always auto-scroll to bottom
    scrollToBottom("smooth");
    isNearBottomRef.current = true;
  }, [messagesCount, scrollToBottom]);

  useEffect(() => {
    // While streaming tokens, only scroll if the user is already near bottom
    if (isNearBottomRef.current) {
      scrollToBottom("auto");
    }
  }, [messages, toolUsages, scrollToBottom]);

  const welcomeCards = [
    {
      title: "Research",
      description: "Search the web for current trends",
      query: "Search the web for the latest AI trends and releases",
      icon: <Search size={18} />,
      color: "var(--accent-cyan)",
      glowColor: "rgba(6, 214, 214, 0.08)",
      borderColor: "rgba(6, 214, 214, 0.1)",
    },
    {
      title: "Create Website",
      description: "Generate a full Next.js project",
      query: "Create a modern responsive website for a creative agency",
      icon: <Code size={18} />,
      color: "var(--accent-purple)",
      glowColor: "rgba(139, 92, 246, 0.08)",
      borderColor: "rgba(139, 92, 246, 0.1)",
    },
    {
      title: "Generate Image",
      description: "Create AI art or UI mockups",
      query: "Generate a highly detailed futuristic city landscape at night",
      icon: <Compass size={18} />,
      color: "var(--accent-cyan)",
      glowColor: "rgba(6, 214, 214, 0.08)",
      borderColor: "rgba(6, 214, 214, 0.1)",
    },
    {
      title: "Analyze Document",
      description: "Query indexed knowledge base",
      query: "List my uploaded knowledge base documents and summarize them",
      icon: <FileText size={18} />,
      color: "var(--accent-purple)",
      glowColor: "rgba(139, 92, 246, 0.08)",
      borderColor: "rgba(139, 92, 246, 0.1)",
    },
    {
      title: "Code Assistant",
      description: "Refactor, review, or debug code",
      query: "Can you review my codebase and suggest performance optimizations?",
      icon: <GraduationCap size={18} />,
      color: "var(--accent-cyan)",
      glowColor: "rgba(6, 214, 214, 0.08)",
      borderColor: "rgba(6, 214, 214, 0.1)",
    },
    {
      title: "Voice Assistant",
      description: "Have a real-time voice chat",
      query: "Start voice mode and help me brainstorm ideas.",
      icon: <Compass size={18} />,
      color: "var(--accent-purple)",
      glowColor: "rgba(139, 92, 246, 0.08)",
      borderColor: "rgba(139, 92, 246, 0.1)",
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 16, scale: 0.96 },
    show: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: { type: "spring" as const, stiffness: 300, damping: 24 },
    },
  };

  // ── Empty State: Futuristic Welcome ──
  if (messages.length === 0) {
    return (
      <HomePage
        onSendHint={onSendHint}
        projectsList={projectsList}
        onSwitchProject={onSwitchProject}
        activeView={activeView}
      />
    );
  }

  const lastAssistantMessage = [...messages].reverse().find(m => m.role === "assistant");
  const hasMetadata = lastAssistantMessage?.metadata && Object.keys(lastAssistantMessage.metadata).length > 0;
  
  return (
    <div style={{ display: "flex", height: "100%", width: "100%", overflow: "hidden" }}>
      <div className="messages-area" ref={containerRef} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div className="messages-container" style={{ width: "100%", maxWidth: "768px", padding: "24px 16px" }}>
        {messages.map((msg, idx) => {
          const isLastAssistant =
            msg.role === "assistant" &&
            (idx === messages.length - 1 || messages[idx + 1]?.role === "user");

          return (
            <MessageBubble
              key={msg.id || idx}
              message={msg}
              toolUsages={toolUsages}
              searchStatus={searchStatus}
              agentProgress={agentProgress}
              onOpenArtifact={onOpenArtifact}
              onSendHint={onSendHint}
              onRegenerate={onRegenerate}
              activeView={activeView}
              isGenerating={isStreaming && isLastAssistant}
            />
          );
        })}
        {isStreaming && messages.length > 0 && messages[messages.length - 1].role === "user" && (
          <AuraThinkingState />
        )}
        <div ref={bottomRef} />
      </div>
      </div>
    </div>
  );
}

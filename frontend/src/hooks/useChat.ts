/**
 * AURA AI useChat Hook
 * Core chat state management with streaming support.
 * Enhanced with retry, cancellation, and request state machine.
 */

"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { AgentProgress, Message, ToolUsage } from "@/types";
import { sendMessage as apiSend, fetchConversation, API_BASE } from "@/lib/api";
import { parseSSEStream } from "@/lib/stream";

interface UseChatOptions {
  onConversationCreated?: (id: string) => void;
  onTitleUpdate?: () => void;
  onProjectLinked?: (projectId: string) => void;
  onError?: (message: string, retryable: boolean) => void;
}

export type RequestState = "idle" | "sending" | "receiving" | "completed" | "retrying" | "failed" | "cancelled";

interface ActiveModelInfo {
  provider: string;
  model: string;
  fallback?: boolean;
}

interface UseChatReturn {
  messages: Message[];
  requestState: RequestState;
  isStreaming: boolean;
  isPaused: boolean;
  currentConversationId: string | null;
  toolUsages: ToolUsage[];
  searchStatus: string | null;
  agentMode: boolean;
  agentProgress: AgentProgress[];
  lastError: string | null;
  lastErrorRetryable: boolean;
  activeModel: ActiveModelInfo | null;
  autoReconnecting: boolean;
  setAgentMode: (mode: boolean) => void;
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
  pauseGeneration: () => Promise<void>;
  resumeGeneration: () => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
  clearChat: () => void;
  selectConversation: (id: string | null) => void;
  retryLast: () => Promise<void>;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [toolUsages, setToolUsages] = useState<ToolUsage[]>([]);
  const [searchStatus, setSearchStatus] = useState<string | null>(null);
  const [agentMode, setAgentMode] = useState(false);
  const [agentProgress, setAgentProgress] = useState<AgentProgress[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);
  const [lastErrorRetryable, setLastErrorRetryable] = useState(false);
  const [activeModel, setActiveModel] = useState<ActiveModelInfo | null>(null);
  const [autoReconnecting, setAutoReconnecting] = useState(false);

  const abortRef = useRef<(() => void) | null>(null);
  const lastUserMessageRef = useRef<string>("");
  const lastConversationIdRef = useRef<string | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;
  const autoReconnectCountRef = useRef(0);
  const maxAutoReconnects = 2;

  // Load conversation messages
  const loadConversation = useCallback(async (conversationId: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("aura_access_token") : null;
    if (!token) return;
    try {
      const detail = await fetchConversation(conversationId);
      setMessages(detail.messages);
      setCurrentConversationId(conversationId);
      setToolUsages([]);
      setAgentProgress([]);
      setIsPaused(false);
      setRequestState("idle");
      setLastError(null);
    } catch (err) {
      console.warn("Failed to load conversation:", err);
    }
  }, []);

  // Clear chat state
  const clearChat = useCallback(() => {
    setMessages([]);
    setCurrentConversationId(null);
    setToolUsages([]);
    setAgentProgress([]);
    setIsPaused(false);
    setRequestState("idle");
    setLastError(null);
    setActiveModel(null);
    retryCountRef.current = 0;
  }, []);

  const selectConversation = useCallback((id: string | null) => {
    setCurrentConversationId(id);
  }, []);

  // Send message and process stream
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || requestState === "sending" || requestState === "receiving") return;

      lastUserMessageRef.current = content;
      lastConversationIdRef.current = currentConversationId;
      retryCountRef.current = 0;
      autoReconnectCountRef.current = 0;

      // Add user message to UI immediately
      const userMsg: Message = {
        id: `temp-${Date.now()}`,
        conversation_id: currentConversationId || "",
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      // Add placeholder assistant message for streaming
      const assistantMsg: Message = {
        id: `temp-assistant-${Date.now()}`,
        conversation_id: currentConversationId || "",
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        isStreaming: true,
        metadata: { thinking: [] },
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setRequestState("sending");
      setIsStreaming(true);
      setIsPaused(false);
      setToolUsages([]);
      setSearchStatus(null);
      setAgentProgress([]);
      setLastError(null);

      try {
        const { stream, abort } = apiSend(content, currentConversationId || undefined, agentMode);
        abortRef.current = abort;

        setRequestState("receiving");

        await parseSSEStream(stream, {
          onConversationId: (id) => {
            setCurrentConversationId(id);
            setMessages((prev) =>
              prev.map((m) =>
                m.conversation_id === "" ? { ...m, conversation_id: id } : m
              )
            );
            lastConversationIdRef.current = id;
            options.onConversationCreated?.(id);
          },

          onToken: (token) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + token,
                };
              }
              return updated;
            });
          },

          onToolUse: (toolName, params) => {
            setToolUsages((prev) => [
              ...prev,
              {
                name: toolName,
                params: params as Record<string, unknown> | undefined,
                isLoading: true,
              },
            ]);
          },

          onToolResult: (result, success) => {
            setToolUsages((prev) => {
              const updated = [...prev];
              const lastTool = updated[updated.length - 1];
              if (lastTool) {
                updated[updated.length - 1] = {
                  ...lastTool,
                  result,
                  success,
                  isLoading: false,
                };
              }
              return updated;
            });
          },

          onSearch: (status, metadata) => {
            setSearchStatus(status);
            if (metadata?.metrics) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    metadata: {
                      ...last.metadata,
                      search_metrics: metadata.metrics,
                    },
                  };
                }
                return updated;
              });
            }
          },

          onThinking: (detail, step, status) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                const currentThinking =
                  (last.metadata?.thinking as Array<{
                    step: string;
                    status: string;
                    detail: string;
                  }>) || [];
                const idx = currentThinking.findIndex((t) => t.step === step);
                let newThinking = [...currentThinking];
                if (idx === -1) {
                  newThinking.push({ step, status, detail });
                } else {
                  newThinking[idx] = { step, status, detail };
                }
                updated[updated.length - 1] = {
                  ...last,
                  metadata: {
                    ...last.metadata,
                    thinking: newThinking,
                  },
                };
              }
              return updated;
            });
          },

          onAgentProgress: (progress) => {
            setAgentProgress((previous) => {
              const existing = previous.findIndex((item) => item.phase === progress.phase);
              if (existing === -1) return [...previous, progress];
              const updated = [...previous];
              updated[existing] = progress;
              return updated;
            });
          },

          onDone: (metadata) => {
            if (metadata?.project_id) {
              options.onProjectLinked?.(metadata.project_id as string);
            }
            
            // Extract model metadata from DONE event
            if (metadata?.model) {
              setActiveModel({
                provider: metadata.model.provider,
                model: metadata.model.model,
                fallback: metadata.model.fallback,
              });
            }
            
            setMessages((prev) =>
              prev.map((m) =>
                m.isStreaming
                  ? { ...m, isStreaming: false, metadata: { ...m.metadata, ...metadata } }
                  : m
              )
            );
            setIsStreaming(false);
            setRequestState("completed");
            abortRef.current = null;
            setSearchStatus(null);
            retryCountRef.current = 0;
            options.onTitleUpdate?.();
          },

          onError: (errorMsg) => {
            const isRetryable = errorMsg.retryable !== false;
            const category = errorMsg.category || "unknown";
            const statusCode = errorMsg.status_code;

            // Build user-friendly message
            let friendlyMsg = errorMsg.message || "An error occurred.";
            if (category === "cancelled") {
              friendlyMsg = "Generation was cancelled.";
            } else if (statusCode === 429 || errorMsg.message?.includes("rate limit")) {
              friendlyMsg =
                "Too many requests right now. Please wait a moment before trying again.";
            } else if (statusCode === 401 || errorMsg.message?.includes("authentication")) {
              friendlyMsg =
                "Session expired. Please log in again.";
            } else if (category === "timeout" || statusCode === 504) {
              friendlyMsg =
                "The AI service is taking too long to respond. Please try again.";
            } else if (category === "transient" || statusCode === 502 || statusCode === 503) {
              friendlyMsg =
                "AI service is temporarily unavailable. Your message is safe. You can retry.";
            } else if (statusCode === 400 || category === "permanent") {
              friendlyMsg =
                "Invalid request. Please check your message and try again.";
            } else if (errorMsg.message?.includes("Connection error")) {
              friendlyMsg =
                "Connection interrupted. Check your connection and retry.";
            }

            // Auto-reconnect for retryable errors (network, timeout, transient)
            const shouldAutoReconnect = isRetryable && 
              autoReconnectCountRef.current < maxAutoReconnects &&
              (category === "network" || category === "timeout" || category === "transient" || category === "server_error" || category === "rate_limit");

            if (shouldAutoReconnect && !autoReconnecting) {
              autoReconnectCountRef.current += 1;
              setAutoReconnecting(true);
              setLastError(`Connection lost. Auto-reconnecting... (attempt ${autoReconnectCountRef.current}/${maxAutoReconnects})`);
              
              // Small delay before reconnecting
              setTimeout(() => {
                setAutoReconnecting(false);
                retryLast();
              }, 1500 * autoReconnectCountRef.current);
              
              return; // Don't set failed state yet, wait for retry
            }

            setLastError(friendlyMsg);
            setLastErrorRetryable(isRetryable);
            setRequestState("failed");
            setIsStreaming(false);

            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content || friendlyMsg,
                  isStreaming: false,
                };
              }
              return updated;
            });

            abortRef.current = null;
            options.onError?.(friendlyMsg, isRetryable);
          },
        });
      } catch (err) {
        const isRetryable = !(err as Error).message?.includes("cancelled");
        const friendlyMsg = isRetryable
          ? "Connection error. Please retry."
          : "Generation was cancelled.";
        setLastError(friendlyMsg);
        setLastErrorRetryable(isRetryable);
        setRequestState("failed");
        setIsStreaming(false);
        abortRef.current = null;

        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: last.content || friendlyMsg,
              isStreaming: false,
            };
          }
          return updated;
        });
      }
    },
    [agentMode, currentConversationId, requestState, options]
  );

  // Stop streaming
  const stopGeneration = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setIsStreaming(false);
    setRequestState("cancelled");
    setIsPaused(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
    // Notify backend to stop
    void fetch(`${API_BASE}/chat/stop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("aura_access_token") || ""}`,
      },
      body: JSON.stringify({ conversationId: currentConversationId }),
    }).catch(() => {});
  }, [currentConversationId]);

  // Pause generation flow
  const pauseGeneration = useCallback(async () => {
    if (!currentConversationId) return;
    try {
      const token = localStorage.getItem("aura_access_token") || "";
      const resp = await fetch(`${API_BASE}/chat/pause`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ conversation_id: currentConversationId }),
      });
      if (resp.ok) {
        setIsPaused(true);
      }
    } catch (err) {
      console.warn("Failed to pause chat stream:", err);
    }
  }, [currentConversationId]);

  // Resume generation flow
  const resumeGeneration = useCallback(async () => {
    if (!currentConversationId) return;
    try {
      const token = localStorage.getItem("aura_access_token") || "";
      const resp = await fetch(`${API_BASE}/chat/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ conversation_id: currentConversationId }),
      });
      if (resp.ok) {
        setIsPaused(false);
      }
    } catch (err) {
      console.warn("Failed to resume chat stream:", err);
    }
  }, [currentConversationId]);

  // Retry last failed message
  const retryLast = useCallback(async () => {
    if (requestState !== "failed") return;
    if (!lastUserMessageRef.current.trim()) return;

    setLastError(null);
    setLastErrorRetryable(false);
    retryCountRef.current += 1;

    if (retryCountRef.current > maxRetries) {
      setLastError("Maximum retry attempts reached. Please try again later.");
      setRequestState("failed");
      return;
    }

    setRequestState("retrying");
    await sendMessage(lastUserMessageRef.current);
  }, [requestState, sendMessage]);

  // Regenerate last assistant response
  const regenerateMessage = useCallback(
    async (messageId: string) => {
      const idx = messages.findIndex((m) => m.id === messageId);
      if (idx === -1) return;

      const userMsg = messages[idx - 1];
      if (!userMsg || userMsg.role !== "user") return;

      setMessages((prev) => prev.slice(0, idx));
      setIsStreaming(false);
      setRequestState("idle");
      setLastError(null);
      await sendMessage(userMsg.content);
    },
    [messages, sendMessage]
  );

  return {
    messages,
    requestState,
    isStreaming,
    isPaused,
    currentConversationId,
    toolUsages,
    searchStatus,
    agentMode,
    agentProgress,
    lastError,
    lastErrorRetryable,
    activeModel,
    autoReconnecting,
    setAgentMode,
    sendMessage,
    stopGeneration,
    pauseGeneration,
    resumeGeneration,
    regenerateMessage,
    retryLast,
    loadConversation,
    clearChat,
    selectConversation,
  };
}

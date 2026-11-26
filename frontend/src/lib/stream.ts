/**
 * AURA AI SSE Stream Parser
 * Parses Server-Sent Events from the chat endpoint with robust format handling.
 */

import type { AgentProgress, ChatEvent, ChatEventType } from "@/types";

export interface StreamCallbacks {
  onConversationId?: (id: string) => void;
  onToken?: (token: string) => void;
  onToolUse?: (toolName: string, params?: Record<string, unknown>) => void;
  onToolResult?: (result: string, success: boolean) => void;
  onSearch?: (status: string, metadata?: Record<string, unknown>) => void;
  onThinking?: (detail: string, step: string, status: string) => void;
  onAgentProgress?: (progress: AgentProgress) => void;
  onDone?: (metadata?: Record<string, unknown>) => void;
  onError?: (error: { message: string; retryable?: boolean; category?: string; status_code?: number } | string) => void;
}

/**
 * Parse an SSE stream and invoke callbacks for each event type.
 */
export async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  callbacks: StreamCallbacks
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete events (separated by double newline)
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || ""; // Keep incomplete part

      for (const part of parts) {
        if (!part.trim()) continue;

        const event = parseSSEEvent(part);
        if (!event) continue;

        switch (event.event) {
          case "conversation_id":
            callbacks.onConversationId?.(event.data.conversation_id || "");
            break;
          case "token":
            callbacks.onToken?.(event.data.content || "");
            break;
          case "tool_use":
            callbacks.onToolUse?.(
              event.data.content,
              event.data.metadata as Record<string, unknown> | undefined
            );
            break;
          case "tool_result":
            callbacks.onToolResult?.(
              event.data.content,
              (event.data.metadata as { success?: boolean })?.success ?? true
            );
            break;
          case "search":
          case "planner":
            callbacks.onSearch?.(
              event.data.content,
              event.data.metadata as Record<string, unknown> | undefined
            );
            break;
          case "thinking": {
            const metadata = event.data.metadata as { step?: string; status?: string } | undefined;
            if (metadata?.step && metadata.status) {
              callbacks.onThinking?.(
                event.data.content,
                metadata.step,
                metadata.status
              );
            }
            break;
          }
          case "agent_progress": {
            const metadata = event.data.metadata as Partial<AgentProgress> | undefined;
            if (metadata?.phase && metadata.status) {
              callbacks.onAgentProgress?.({
                phase: metadata.phase,
                status: metadata.status,
                detail: metadata.detail || event.data.content || ""
              });
            }
            break;
          }
          case "done":
            callbacks.onDone?.(event.data.metadata as Record<string, unknown> | undefined);
            break;
          case "error":
            callbacks.onError?.(event.data as { message: string; retryable?: boolean; category?: string; status_code?: number });
            break;
        }
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") {
      callbacks.onError?.({
        message: (err as Error).message,
        retryable: true,
        category: "unknown",
      });
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Parse a single SSE event block supporting both standard and compact SSE formats.
 */
function parseSSEEvent(raw: string): ChatEvent | null {
  let eventType: ChatEventType = "token";
  let dataStr = "";

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (trimmed.startsWith("event:")) {
      eventType = trimmed.slice(6).trim() as ChatEventType;
    } else if (trimmed.startsWith("data:")) {
      dataStr = trimmed.slice(5).trim();
    }
  }

  if (!dataStr) return null;

  try {
    const data = JSON.parse(dataStr);
    return { event: eventType, data };
  } catch {
    return { event: eventType, data: { content: dataStr } };
  }
}

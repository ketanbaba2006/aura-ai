/**
 * AURA AI API Client
 * Handles all backend communication.
 */

import type { Conversation, ConversationDetail, ToolInfo, ToolResult } from "@/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Default fetch timeout in milliseconds
const FETCH_TIMEOUT_MS = parseInt(process.env.NEXT_PUBLIC_FETCH_TIMEOUT_MS || "300000", 10);

// ─── Helpers ─────────────────────────────────────────────

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: NodeJS.Timeout | null = null;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("Request timed out")), ms);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timer) clearTimeout(timer);
  });
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers || {});
  
  // Attach Access Token
  const token = localStorage.getItem("aura_access_token");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  // Attach CSRF Token for state-modifying requests
  if (options.method && !["GET", "HEAD", "OPTIONS"].includes(options.method)) {
    const csrf = localStorage.getItem("aura_csrf_token");
    if (csrf) {
      headers.set("x-csrf-token", csrf);
    }
  }

  const mergedOptions: RequestInit = { ...options, headers, credentials: "include" };
  let res = await withTimeout(fetch(url, mergedOptions), FETCH_TIMEOUT_MS);

  // If 401 Unauthorized, try to run a silent refresh
  if (res.status === 401 && !url.includes("/auth/refresh") && !url.includes("/auth/login")) {
    try {
      const refreshRes = await withTimeout(
        fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include"
        }),
        FETCH_TIMEOUT_MS
      );
      
      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        if (refreshData.success) {
          const newToken = refreshData.access_token;
          localStorage.setItem("aura_access_token", newToken);
          
          // Re-attempt request
          headers.set("Authorization", `Bearer ${newToken}`);
          res = await withTimeout(fetch(url, { ...options, headers, credentials: "include" }), FETCH_TIMEOUT_MS);
        } else {
          localStorage.removeItem("aura_access_token");
          localStorage.removeItem("aura_csrf_token");
          if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("aura-logout"));
          }
        }
      } else {
        localStorage.removeItem("aura_access_token");
        localStorage.removeItem("aura_csrf_token");
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("aura-logout"));
        }
      }
    } catch (err) {
      console.warn("Silent token refresh failed:", err);
      localStorage.removeItem("aura_access_token");
      localStorage.removeItem("aura_csrf_token");
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("aura-logout"));
      }
    }
  } else if (res.status === 401) {
    localStorage.removeItem("aura_access_token");
    localStorage.removeItem("aura_csrf_token");
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("aura-logout"));
    }
  }

  return res;
}

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetchWithAuth(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }

  return res.json();
}

// ─── Health ──────────────────────────────────────────────

export async function checkHealth(): Promise<{
  status: string;
  model: string;
  tools_loaded: number;
}> {
  // Use plain fetch for checkHealth to prevent authentication checks causing loops on startup
  const res = await fetch(`${API_BASE}/health`, {
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}

// ─── Conversations ───────────────────────────────────────

export async function fetchConversations(): Promise<Conversation[]> {
  return fetchJSON("/conversations");
}

export async function createConversation(title?: string): Promise<Conversation> {
  return fetchJSON("/conversations", {
    method: "POST",
    body: JSON.stringify({ title: title || "New Conversation" }),
  });
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  return fetchJSON(`/conversations/${id}`);
}

export async function updateConversationTitle(
  id: string,
  title: string
): Promise<Conversation> {
  return fetchJSON(`/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(id: string): Promise<void> {
  await fetchJSON(`/conversations/${id}`, { method: "DELETE" });
}

// ─── Chat (SSE Stream) ──────────────────────────────────

export function sendMessage(
  message: string,
  conversationId?: string,
  autonomous = false,
  activeFiles?: any[]
): { stream: ReadableStream<Uint8Array>; abort: () => void } {
  const controller = new AbortController();
  let settled = false;

  const body = JSON.stringify({
    message,
    conversation_id: conversationId || null,
    autonomous,
    active_files: activeFiles || [],
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });

  const token = localStorage.getItem("aura_access_token");
  const csrf = localStorage.getItem("aura_csrf_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (csrf) {
    headers["x-csrf-token"] = csrf;
  }

  const streamPromise = (async () => {
    try {
      const res = await withTimeout(
        fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers,
          body,
          signal: controller.signal,
          credentials: "include",
        }),
        FETCH_TIMEOUT_MS
      );

      // 401 on a stream — do NOT retry (would duplicate the AI request).
      // Surface the error so the frontend can handle token refresh gracefully.
      if (res.status === 401) {
        localStorage.removeItem("aura_access_token");
        localStorage.removeItem("aura_csrf_token");
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("aura-logout"));
        }
        throw new Error("Authentication expired. Please log in again.");
      }

      if (!res.ok) {
        throw new Error(`Chat API error: ${res.status}`);
      }
      if (!res.body) {
        throw new Error("No response body");
      }
      return res.body;
    } catch (err) {
      if (!settled && (err as Error).name !== "AbortError") {
        settled = true;
      }
      throw err;
    }
  })();

  // Wrap in a ReadableStream that resolves the fetch first
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        const body = await streamPromise;
        if (!body) {
          throw new Error("No response body available in streamPromise");
        }
        const reader = body.getReader();

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            controller.close();
            break;
          }
          controller.enqueue(value);
        }
      } catch (err) {
        settled = true;
        if ((err as Error).name !== "AbortError") {
          controller.error(err);
        }
      }
    },
  });

  return {
    stream,
    abort: () => {
      settled = true;
      controller.abort();
    },
  };
}

// ─── Tools ───────────────────────────────────────────────

export async function fetchTools(): Promise<ToolInfo[]> {
  return fetchJSON("/tools");
}

export async function executeTool(
  name: string,
  params: Record<string, unknown>
): Promise<ToolResult> {
  return fetchJSON(`/tools/${name}/execute`, {
    method: "POST",
    body: JSON.stringify({ params }),
  });
}

// ─── Deep Research (Isolated from Chat) ──────────────────

export function startDeepResearch(
  topic: string,
  conversationId?: string,
  depth: string = "standard"
): { stream: ReadableStream<Uint8Array>; abort: () => void } {
  const controller = new AbortController();

  const body = JSON.stringify({
    topic,
    conversation_id: conversationId || null,
    depth,
  });

  const token = localStorage.getItem("aura_access_token");
  const csrf = localStorage.getItem("aura_csrf_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (csrf) headers["x-csrf-token"] = csrf;

  const streamPromise = fetch(`${API_BASE}/research/start`, {
    method: "POST",
    headers,
    body,
    signal: controller.signal,
    credentials: "include",
  }).then(async (res) => {
    if (!res.ok) throw new Error(`Research API error: ${res.status}`);
    if (!res.body) throw new Error("No response body");
    return res.body;
  });

  const stream = new ReadableStream<Uint8Array>({
    async start(ctrl) {
      try {
        const body = await streamPromise;
        if (!body) throw new Error("No response body");
        const reader = body.getReader();
        while (true) {
          const { done, value } = await reader.read();
          if (done) { ctrl.close(); break; }
          ctrl.enqueue(value);
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") ctrl.error(err);
      }
    },
  });

  return { stream, abort: () => controller.abort() };
}

export async function fetchResearchHistory(): Promise<any[]> {
  return fetchJSON("/research/history");
}

export async function fetchResearchReport(reportId: string): Promise<any> {
  return fetchJSON(`/research/report/${reportId}`);
}

export async function fetchResearchSettings(): Promise<Record<string, string>> {
  return fetchJSON("/research/settings");
}

export async function updateResearchSetting(key: string, value: string): Promise<any> {
  return fetchJSON("/research/settings", {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

export async function cancelResearch(conversationId: string): Promise<any> {
  return fetchJSON("/research/cancel", {
    method: "POST",
    body: JSON.stringify({ conversation_id: conversationId }),
  });
}

export function getResearchDownloadUrl(path: string): string {
  return `${API_BASE}/research/download?path=${encodeURIComponent(path)}`;
}

/**
 * AURA AI useConversations Hook
 * Manages conversation CRUD state.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { Conversation } from "@/types";
import {
  fetchConversations,
  createConversation as apiCreate,
  deleteConversation as apiDelete,
  updateConversationTitle as apiUpdateTitle,
} from "@/lib/api";

import { useAuth } from "@/context/AuthContext";

export function useConversations() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load conversations on mount
  const refresh = useCallback(async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("aura_access_token") : null;
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      const data = await fetchConversations();
      setConversations(data);
    } catch (err) {
      console.warn("Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      refresh();
    }
  }, [refresh, user]);

  const createConversation = useCallback(async (title?: string) => {
    const conv = await apiCreate(title);
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    return conv;
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      await apiDelete(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
      }
    },
    [activeId]
  );

  const updateTitle = useCallback(async (id: string, title: string) => {
    const updated = await apiUpdateTitle(id, title);
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
    );
  }, []);

  const selectConversation = useCallback((id: string | null) => {
    setActiveId(id);
  }, []);

  return {
    conversations,
    activeId,
    isLoading,
    refresh,
    createConversation,
    deleteConversation,
    updateTitle,
    selectConversation,
  };
}

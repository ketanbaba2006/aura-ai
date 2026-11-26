/**
 * AURA OS App Shell
 * Main layout: particle background + sidebar + dynamic view content.
 */

"use client";

import { useState, useCallback, useEffect } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { AuraAvatar } from "@/components/chat/AuraAvatar";
import type { ActiveView, AuraState } from "@/types";
import { checkHealth } from "@/lib/api";
import { StatusBadge } from "@/components/chat/StatusBadge";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";

// Removed obsolete page views (Memory, Knowledge, etc.)

import { useAuth } from "@/context/AuthContext";
import { LoginScreen } from "@/components/auth/LoginScreen";
import { HomePage } from "@/components/pages/HomePage";
import { NotebookWorkspace } from "@/components/notebook/NotebookWorkspace";
import { LiveSandbox } from "@/components/sandbox/LiveSandbox";
import { FolderSync, XCircle, Archive, Menu } from "lucide-react";
import { fetchWithAuth } from "@/lib/api";
import { AuraSplashScreen } from "./AuraSplashScreen";
import { LivePreviewBuilder } from "@/components/builders/LivePreviewBuilder";
import { DeepResearchPage } from "@/components/pages/DeepResearchPage";


export function AppShell() {
  const { user, loading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [isOnline, setIsOnline] = useState(true);
  const [activeProject, setActiveProject] = useState<any | null>(null);
  const [projectsList, setProjectsList] = useState<any[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<{
    title: string;
    content: string;
    language?: string;
  } | null>(null);

  // --- AURA OS Boot Sequence State ---
  const [isBooting, setIsBooting] = useState(true);
  // ------------------------------------


  // Poll server health every 10 seconds
  useEffect(() => {
    const pollHealth = async () => {
      try {
        const health = await checkHealth();
        setIsOnline(health.status === "healthy");
      } catch (err) {
        setIsOnline(false);
      }
    };
    pollHealth();
    const interval = setInterval(pollHealth, 10000);
    return () => clearInterval(interval);
  }, []);




  const {
    conversations,
    activeId,
    refresh: refreshConversations,
    createConversation,
    deleteConversation,
    selectConversation,
  } = useConversations();

  const {
    messages,
    isStreaming,
    isPaused,
    toolUsages,
    searchStatus,
    agentMode,
    agentProgress,
    setAgentMode,
    sendMessage,
    stopGeneration,
    pauseGeneration,
    resumeGeneration,
    regenerateMessage,
    loadConversation,
    clearChat,
    activeModel,
  } = useChat({
    onConversationCreated: (id) => {
      selectConversation(id);
      refreshConversations();
    },
    onTitleUpdate: () => {
      refreshConversations();
    },
    onProjectLinked: (projectId) => {
      fetchActiveProject();
    }
  });

  useEffect(() => {
    setAgentMode(activeView === "website-builder" || activeView === "app-builder");
  }, [activeView, setAgentMode]);

  const fetchActiveProject = useCallback(async () => {
    if (!activeId) {
      setActiveProject(null);
      return;
    }
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/projects/active?conversation_id=${activeId}`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.active) {
          setActiveProject(data.project);
        } else {
          setActiveProject(null);
        }
      }
    } catch (e) {
      console.warn("Failed to fetch active project:", e);
    }
  }, [activeId]);

  const fetchProjectsList = useCallback(async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/projects`);
      if (resp.ok) {
        const data = await resp.json();
        setProjectsList(data);
      }
    } catch (e) {
      console.warn("Failed to fetch projects list:", e);
    }
  }, []);

  useEffect(() => {
    fetchActiveProject();
    fetchProjectsList();
  }, [activeId, fetchActiveProject, fetchProjectsList]);

  useEffect(() => {
    if (!isStreaming) {
      fetchActiveProject();
      fetchProjectsList();
    }
  }, [isStreaming, fetchActiveProject, fetchProjectsList]);

  // Result First Preview Auto Loader
  useEffect(() => {
    if (activeProject && (activeView === "website-builder" || activeView === "app-builder") && !selectedArtifact) {
      const loadIndexFile = async () => {
        try {
          const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
          const path = `Projects/${activeProject.slug}/index.html`;
          const resp = await fetchWithAuth(`${apiBase}/files/read?path=${encodeURIComponent(path)}`);
          if (resp.ok) {
            const data = await resp.json();
            setSelectedArtifact({
              title: data.name,
              content: data.content,
              language: "html",
            });
          }
        } catch (e) {
          console.warn("Failed to auto-load index.html for preview:", e);
        }
      };
      loadIndexFile();
    }
  }, [activeProject, activeView, selectedArtifact]);

  const handleSwitchProject = async (projectId: string) => {
    if (!activeId || !projectId) return;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/projects/active`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: activeId, project_id: projectId }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setActiveProject(data.project);
        refreshConversations();
      }
    } catch (e) {
      console.warn("Failed to switch project:", e);
    }
  };

  const handleResetProject = async () => {
    if (!activeId) return;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/projects/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: activeId }),
      });
      if (resp.ok) {
        setActiveProject(null);
      }
    } catch (e) {
      console.warn("Failed to reset project:", e);
    }
  };

  const handleArchiveProject = async () => {
    if (!activeProject || !activeId) return;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/projects/archive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: activeProject.id, archived: true }),
      });
      if (resp.ok) {
        await handleResetProject();
        await fetchProjectsList();
      }
    } catch (e) {
      console.warn("Failed to archive project:", e);
    }
  };

  const handleNewChat = useCallback(() => {
    clearChat();
    selectConversation(null);
    setActiveView("chat");
    setSelectedArtifact(null);
  }, [clearChat, selectConversation]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      selectConversation(id);
      loadConversation(id);
      setActiveView("chat");
      setSelectedArtifact(null);
    },
    [selectConversation, loadConversation]
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      if (activeId === id) {
        clearChat();
      }
    },
    [deleteConversation, activeId, clearChat]
  );

  const handleSendHint = useCallback(
    (hint: string) => {
      sendMessage(hint);
    },
    [sendMessage]
  );

  const handleSelectView = useCallback((view: ActiveView) => {
    setActiveView(view);
    setSelectedArtifact(null);
  }, [user]);

  const handleOpenArtifact = useCallback((title: string, content: string, language?: string) => {
    setSelectedArtifact({ title, content, language });
    setActiveView("chat"); // keep chats history active
  }, []);



  // Derive AURA Core state from current activity
  const getAuraState = (): AuraState => {
    if (!isStreaming) return 'idle';
    const activeTool = toolUsages.find((t) => t.isLoading);
    if (activeTool) {
      if (activeTool.name === 'web_search' || activeTool.name === 'knowledge_retrieval') return 'researching';
      return 'thinking';
    }
    if (agentMode) return 'agent';
    if (searchStatus) return 'researching';
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content) return 'generating';
    return 'thinking';
  };

  if (loading || isBooting) {
    return <AuraSplashScreen onComplete={() => setIsBooting(false)} />;
  }

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <>
      <div className="app-shell" style={{ display: "flex", width: "100vw", height: "100vh", overflow: "hidden", background: "var(--bg-void)" }}>
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          onNewChat={handleNewChat}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          activeView={activeView}
          onSelectView={handleSelectView}
          isOnline={isOnline}
        />

        <div className="chat-main" style={{ 
          flex: activeView === "website-builder" || activeView === "app-builder" ? "0 0 30%" : 1, 
          display: "flex", 
          flexDirection: "column", 
          height: "100%", 
          overflow: "hidden", 
          minWidth: 0, 
          borderRight: (activeView === "website-builder" || activeView === "app-builder") ? "1px solid var(--surface-border)" : "none", 
          background: "var(--bg-void)",
          position: "relative"
        }}>
          {/* Header */}
          <div 
            className="chat-header flex items-center px-4"
            style={{ height: "var(--header-height)", background: "transparent", borderBottom: "none" }}
          >
            {/* Sidebar toggle button for mobile/collapsed state if needed, handled in Sidebar normally, but we can add one here if sidebar is closed */}
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} className="mr-3 p-2 rounded-md hover:bg-[var(--surface-glass)] text-[var(--text-secondary)]">
                <Menu size={20} />
              </button>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1 }}>
              <span 
                className="chat-title" 
                style={{ 
                  fontWeight: "500",
                  color: "var(--text-secondary)",
                  fontSize: "15px"
                }}
              >
                {activeId
                  ? conversations.find((c) => c.id === activeId)?.title || "ChatGPT"
                  : "ChatGPT 4o"
                }
              </span>

                      {/* AI Status Badge */}
              <StatusBadge
                isStreaming={isStreaming}
                toolUsages={toolUsages}
                searchStatus={searchStatus}
                activeModel={activeModel}
              />
            </div>
          </div>

          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              height: "calc(100vh - var(--header-height))",
              position: "relative",
            }}
          >
            {activeView === "deep-research" ? (
              <div className="w-full h-full absolute inset-0 z-50 bg-[var(--bg-primary)]">
                <DeepResearchPage />
              </div>
            ) : activeView === "notebook" ? (
              <div className="w-full h-full absolute inset-0 z-50 bg-[var(--bg-primary)]">
                <NotebookWorkspace />
              </div>
            ) : messages.length === 0 ? (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingBottom: "10vh" }}>
                <HomePage
                  onSendHint={handleSendHint}
                  projectsList={projectsList}
                  onSwitchProject={handleSwitchProject}
                  activeView={activeView}
                />
                <div style={{ width: "100%", maxWidth: "768px", marginTop: "16px", zIndex: 10 }}>
                  <ChatInput
                    onSend={sendMessage}
                    onStop={stopGeneration}
                    isStreaming={isStreaming}
                    isPaused={isPaused}
                    onPauseToggle={() => {
                      if (isPaused) {
                        resumeGeneration();
                      } else {
                        pauseGeneration();
                      }
                    }}
                    agentMode={agentMode}
                    onAgentModeChange={setAgentMode}
                    onSwitchView={handleSelectView}
                    activeView={activeView}
                    conversationId={activeId}
                  />
                </div>
              </div>
            ) : (
              <>
                <ChatWindow
                  messages={messages}
                  isStreaming={isStreaming}
                  toolUsages={toolUsages}
                  searchStatus={searchStatus}
                  agentProgress={agentProgress}
                  onSendHint={handleSendHint}
                  onOpenArtifact={handleOpenArtifact}
                  onRegenerate={regenerateMessage}
                  projectsList={projectsList}
                  onSwitchProject={handleSwitchProject}
                  activeView={activeView}
                />
                <ChatInput
                  onSend={sendMessage}
                  onStop={stopGeneration}
                  isStreaming={isStreaming}
                  isPaused={isPaused}
                  onPauseToggle={() => {
                    if (isPaused) {
                      resumeGeneration();
                    } else {
                      pauseGeneration();
                    }
                  }}
                  agentMode={agentMode}
                  onAgentModeChange={setAgentMode}
                  onSwitchView={handleSelectView}
                  activeView={activeView}
                  conversationId={activeId}
                />
              </>
            )}
          </div>
        </div>

        {/* Builder Mode Preview Pane */}
        {(activeView === "website-builder" || activeView === "app-builder") && (
          <div
            className="builder-preview"
            style={{
              flex: 1, // Let it fill the remaining 70% space
              display: "flex",
              flexDirection: "column",
              background: "var(--bg-secondary)",
              position: "relative",
            }}
          >
            <LivePreviewBuilder type={activeView === "website-builder" ? "website" : "app"} />
          </div>
        )}
      </div>
    </>
  );
}

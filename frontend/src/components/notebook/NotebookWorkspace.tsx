"use client";

import React, { useState, useEffect } from "react";
import { SourcePanel } from "./SourcePanel";
import { NotebookChat } from "./NotebookChat";
import { SourceExplorer } from "./SourceExplorer";

export function NotebookWorkspace() {
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [activeExplorerDocId, setActiveExplorerDocId] = useState<string | null>(null);

  // Generate a conversation ID for this session if we don't have one
  // For Notebook, we can use a dedicated session per mount or load it
  const [sessionId, setSessionId] = useState<string>("");
  
  useEffect(() => {
    // Basic session init
    setSessionId("notebook_" + Date.now().toString());
  }, []);

  return (
    <div className="flex h-full w-full bg-[var(--bg-primary)] overflow-hidden">
      {/* LEFT PANE: Source Panel */}
      <div className="w-[300px] shrink-0 border-r border-[var(--surface-border)] bg-[var(--surface-glass)] flex flex-col">
        <SourcePanel 
          sessionId={sessionId}
          selectedDocIds={selectedDocIds}
          onSelectionChange={setSelectedDocIds}
          onSelectExplorer={setActiveExplorerDocId}
        />
      </div>

      {/* CENTER PANE: Chat */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <NotebookChat 
          sessionId={sessionId}
          selectedDocIds={selectedDocIds}
          onCitationClick={(docId) => setActiveExplorerDocId(docId)}
        />
      </div>

      {/* RIGHT PANE: Source Explorer (Collapsible) */}
      {activeExplorerDocId && (
        <div className="w-[350px] shrink-0 border-l border-[var(--surface-border)] bg-[var(--surface-glass)] flex flex-col shadow-lg z-10">
          <SourceExplorer 
            docId={activeExplorerDocId}
            onClose={() => setActiveExplorerDocId(null)}
          />
        </div>
      )}
    </div>
  );
}

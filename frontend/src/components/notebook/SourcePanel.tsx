"use client";

import React, { useState, useEffect, useRef } from "react";
import { Upload, FileText, Check, Loader2, Info } from "lucide-react";
import { fetchWithAuth, API_BASE } from "@/lib/api";

interface SourcePanelProps {
  sessionId: string;
  selectedDocIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onSelectExplorer: (id: string) => void;
}

export function SourcePanel({ sessionId, selectedDocIds, onSelectionChange, onSelectExplorer }: SourcePanelProps) {
  const [docs, setDocs] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/knowledge/documents`);
      const data = await res.json();
      setDocs(data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  };

  useEffect(() => {
    fetchDocs();
    // Poll every 5s just in case backgrounds tasks finish
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetchWithAuth(`${API_BASE}/knowledge/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Upload failed: ${res.status} ${errText}`);
      }
      // Give it a second then fetch
      setTimeout(fetchDocs, 1000);
    } catch (err) {
      console.error("Upload failed", err);
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedDocIds.includes(id)) {
      onSelectionChange(selectedDocIds.filter(d => d !== id));
    } else {
      onSelectionChange([...selectedDocIds, id]);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-[var(--surface-border)] shrink-0">
        <h2 className="text-[16px] font-bold text-[var(--text-primary)] flex items-center gap-2">
          <FileText size={18} /> Sources
        </h2>
        <p className="text-[12px] text-[var(--text-muted)] mt-1">
          Select sources to ground AURA Research.
        </p>
      </div>

      <div className="p-4 shrink-0">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="w-full flex items-center justify-center gap-2 bg-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[var(--text-primary)] rounded-lg py-2 px-4 transition-colors font-medium text-sm disabled:opacity-50"
        >
          {isUploading ? <Loader2 className="animate-spin" size={16} /> : <Upload size={16} />}
          {isUploading ? "Uploading..." : "Add Source"}
        </button>
        <input 
          type="file" 
          ref={fileInputRef}
          onChange={handleUpload}
          className="hidden"
          accept=".pdf,.docx,.txt,.md,.csv"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2">
        {docs.length === 0 && !isUploading && (
          <div className="text-center text-[var(--text-muted)] text-[13px] py-10 px-4">
            No sources available. Upload a document to begin research.
          </div>
        )}
        
        {docs.map(doc => {
          const isSelected = selectedDocIds.includes(doc.id);
          const isProcessing = doc.status === "processing";
          
          return (
            <div 
              key={doc.id}
              className={`flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer ${
                isSelected 
                  ? "border-[var(--accent-cyan)] bg-[rgba(6,182,212,0.1)]" 
                  : "border-[var(--surface-border)] bg-[var(--bg-elevated)] hover:border-[var(--text-muted)]"
              }`}
              onClick={() => {
                if (!isProcessing) toggleSelect(doc.id);
              }}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${isSelected ? "bg-[var(--accent-cyan)] border-[var(--accent-cyan)]" : "border-[var(--text-muted)]"}`}>
                  {isSelected && <Check size={12} className="text-white" />}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[13px] font-medium text-[var(--text-primary)] truncate" title={doc.filename}>
                    {doc.filename}
                  </span>
                  <span className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
                    {isProcessing ? (
                      <><Loader2 size={10} className="animate-spin" /> Processing...</>
                    ) : (
                      <>{doc.chunk_count} segments</>
                    )}
                  </span>
                </div>
              </div>
              
              <button 
                className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--accent-cyan)] hover:bg-[var(--surface-hover)] transition-colors shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectExplorer(doc.id);
                }}
                title="Explore Source"
              >
                <Info size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

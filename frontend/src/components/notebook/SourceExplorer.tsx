"use client";

import React, { useState, useEffect } from "react";
import { X, FileText, Loader2, List, Quote } from "lucide-react";
import { fetchWithAuth, API_BASE } from "@/lib/api";

interface SourceExplorerProps {
  docId: string;
  onClose: () => void;
}

export function SourceExplorer({ docId, onClose }: SourceExplorerProps) {
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetails = async () => {
      setLoading(true);
      try {
        const res = await fetchWithAuth(`${API_BASE}/notebook/source/${docId}/summary`);
        const data = await res.json();
        setDetails(data);
      } catch (err) {
        console.error("Failed to load source details", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [docId]);

  return (
    <div className="flex flex-col h-full bg-[var(--surface-glass)]">
      <div className="p-4 border-b border-[var(--surface-border)] flex items-center justify-between shrink-0">
        <h2 className="text-[14px] font-bold text-[var(--text-primary)] flex items-center gap-2 truncate pr-2">
          <FileText size={16} /> Source Explorer
        </h2>
        <button 
          onClick={onClose}
          className="p-1 rounded hover:bg-[var(--surface-hover)] text-[var(--text-muted)] transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 space-y-3">
            <Loader2 className="animate-spin text-[var(--accent-cyan)]" size={24} />
            <span className="text-[12px] text-[var(--text-muted)]">Analyzing Document...</span>
          </div>
        ) : (
          <>
            <div>
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
                <FileText size={12} /> Summary
              </h3>
              <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-elevated)] p-3 rounded-lg border border-[var(--surface-border)]">
                {details?.summary || "No summary available."}
              </p>
            </div>

            <div>
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
                <List size={12} /> Key Concepts
              </h3>
              <ul className="flex flex-col gap-2">
                {details?.key_concepts?.map((c: string, i: number) => (
                  <li key={i} className="text-[13px] text-[var(--text-primary)] bg-[rgba(6,182,212,0.1)] border border-[var(--accent-cyan)] px-3 py-1.5 rounded-full inline-block self-start w-auto">
                    {c}
                  </li>
                )) || <div className="text-[13px] text-[var(--text-muted)]">No key concepts found.</div>}
              </ul>
            </div>

            <div>
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
                <Quote size={12} /> Key Quotes
              </h3>
              <div className="flex flex-col gap-3">
                {details?.quotes?.map((q: string, i: number) => (
                  <div key={i} className="text-[13px] italic text-[var(--text-secondary)] border-l-2 border-[var(--accent-cyan)] pl-3 py-1">
                    "{q}"
                  </div>
                )) || <div className="text-[13px] text-[var(--text-muted)]">No quotes available.</div>}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

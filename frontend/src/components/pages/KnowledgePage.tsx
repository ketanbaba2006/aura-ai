/**
 * AURA OS Knowledge Base Dashboard Page
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { KnowledgeDocument, KnowledgeChunk } from "@/types";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

export function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const { showToast, showModal } = useNotification();

  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/knowledge/documents`);
      if (resp.ok) {
        const data = await resp.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error("Failed to load documents", e);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/knowledge/upload`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || "Upload ingestion failed.");
      }

      await fetchDocuments();
      showToast(`Ingested ${file.name} successfully!`, "success");
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload file.");
    } finally {
      setIsUploading(false);
      // Reset input
      e.target.value = "";
    }
  };

  const handleDeleteDoc = (id: string) => {
    showModal({
      title: "Confirm Delete Document",
      description: "Are you sure you want to delete this document from the knowledge base?",
      actions: [
        {
          label: "Delete Document",
          variant: "danger",
          onClick: () => executeDeleteDoc(id)
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const executeDeleteDoc = async (id: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/knowledge/documents/${id}`, {
        method: "DELETE",
      });

      if (resp.ok) {
        setDocuments(documents.filter((d) => d.id !== id));
        // Reset search results if they match deleted document chunks
        setSearchResults([]);
        showToast("Document deleted successfully.", "success");
      } else {
        showToast("Failed to delete document.", "error");
      }
    } catch (e) {
      showToast("Error deleting document.", "error");
      console.error("Failed to delete", e);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(
        `${apiBase}/knowledge/search?q=${encodeURIComponent(searchQuery)}&limit=5`
      );
      if (resp.ok) {
        const data = await resp.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      setIsSearching(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="page-container" style={{ padding: "40px", height: "100%", overflowY: "auto" }}>
      <div className="page-header" style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "600", color: "var(--text)", marginBottom: "8px" }}>
          📚 Knowledge Base
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
          Upload files to AURA's local vector index. Files are semantic chunked and immediately retrievable.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
        {/* Left: Document Manager & Uploader */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Uploader Card */}
          <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)" }}>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Ingest New Document</h2>
            
            <div
              style={{
                border: "2px dashed var(--border)",
                borderRadius: "8px",
                padding: "32px 20px",
                textAlign: "center",
                cursor: "pointer",
                background: "rgba(255,255,255,0.01)",
                position: "relative"
              }}
            >
              <input
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                onChange={handleFileUpload}
                disabled={isUploading}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  opacity: 0,
                  cursor: "pointer"
                }}
              />
              <span style={{ fontSize: "32px", display: "block", marginBottom: "8px" }}>📤</span>
              <span style={{ fontSize: "14px", color: "var(--text)", fontWeight: "500", display: "block" }}>
                {isUploading ? "Processing Ingestion..." : "Click or Drag PDF, DOCX, TXT, MD to ingest"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px", display: "block" }}>
                Maximum size 15MB
              </span>
            </div>

            {uploadError && (
              <div style={{ marginTop: "16px", padding: "12px", borderRadius: "6px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--error)", color: "var(--error)", fontSize: "13px" }}>
                {uploadError}
              </div>
            )}
          </div>

          {/* Document list Card */}
          <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", flex: 1 }}>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Indexed Documents</h2>

            {isLoadingDocs ? (
              <div style={{ color: "var(--text-muted)", padding: "20px", textAlign: "center", fontSize: "14px" }}>Loading catalogue...</div>
            ) : documents.length === 0 ? (
              <div style={{ color: "var(--text-muted)", padding: "40px", textAlign: "center", fontSize: "14px" }}>
                No documents indexed yet. Ingest your first document.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "400px", overflowY: "auto" }}>
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      background: "rgba(255,255,255,0.02)",
                      border: "1px solid var(--border)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "500" }}>{doc.filename}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                        {formatSize(doc.file_size)} • {doc.chunk_count} chunks
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteDoc(doc.id)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "4px",
                        background: "rgba(239, 68, 68, 0.1)",
                        color: "#f87171",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        cursor: "pointer",
                        fontSize: "12px"
                      }}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: In-Depth Vector Search Checker */}
        <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
          <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Vector Index Inspector</h2>
          
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
            <input
              type="text"
              className="chat-input-field"
              placeholder="Query terms to inspect indexed chunks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                outline: "none",
                fontSize: "14px"
              }}
            />
            <button
              type="submit"
              disabled={isSearching}
              style={{
                padding: "12px 20px",
                borderRadius: "8px",
                background: "var(--primary)",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontWeight: "500",
                fontSize: "14px"
              }}
            >
              {isSearching ? "Searching..." : "Inspect"}
            </button>
          </form>

          {/* Results List */}
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px", maxHeight: "600px" }}>
            {searchResults.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "80px 20px", fontSize: "14px" }}>
                {searchQuery ? "No matching document chunks found." : "Run a query to retrieve matching document vectors."}
              </div>
            ) : (
              searchResults.map((chunk, idx) => (
                <div
                  key={chunk.chunk_id || idx}
                  style={{
                    padding: "16px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid var(--border)"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "8px" }}>
                    <span style={{ color: "var(--primary)", fontWeight: "500" }}>
                      📁 {chunk.filename}
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>
                      Relevance Score: <strong style={{ color: "var(--success)" }}>{(chunk.score * 100).toFixed(1)}%</strong>
                    </span>
                  </div>
                  <div style={{ color: "var(--text)", fontSize: "13.5px", lineHeight: "1.5", fontStyle: "italic", whiteSpace: "pre-wrap" }}>
                    "{chunk.content}"
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Map, FileText, Headphones, HelpCircle, FileClock, Loader2, Sparkles } from "lucide-react";
import { fetchWithAuth, API_BASE } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface NotebookChatProps {
  sessionId: string;
  selectedDocIds: string[];
  onCitationClick: (docId: string) => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: any[];
}

export function NotebookChat({ sessionId, selectedDocIds, onCitationClick }: NotebookChatProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isGenerating) return;
    
    if (selectedDocIds.length === 0) {
      alert("Please select at least one source document from the left panel.");
      return;
    }

    const query = input;
    setInput("");
    setIsGenerating(true);
    setMessages(prev => [...prev, { role: "user", content: query }]);
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetchWithAuth(`${API_BASE}/notebook/chat/stream`, {
        method: "POST",
        body: JSON.stringify({
          query,
          conversation_id: sessionId,
          doc_ids: selectedDocIds
        })
      });

      if (!res.body) throw new Error("No body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      let assistantContent = "";
      let metadata: any = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") continue;
            try {
              const event = JSON.parse(dataStr);
              if (event.content) {
                assistantContent += event.content;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = assistantContent;
                  return newMsgs;
                });
              }
              if (event.metadata && event.metadata.citations) {
                metadata = event.metadata;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].citations = metadata.citations;
                  return newMsgs;
                });
              }
            } catch (e) {
              // Parse error
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content = "Failed to connect to AURA Research Engine.";
        return newMsgs;
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateSpecial = async (task_type: string) => {
    if (selectedDocIds.length === 0) {
      alert("Please select at least one source document.");
      return;
    }
    
    setIsGenerating(true);
    setMessages(prev => [...prev, { role: "user", content: `Generate ${task_type.replace("_", " ")}` }]);
    
    try {
      const res = await fetchWithAuth(`${API_BASE}/notebook/generate`, {
        method: "POST",
        body: JSON.stringify({
          task_type,
          conversation_id: sessionId,
          doc_ids: selectedDocIds
        })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.content }]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  // Custom Markdown renderer for citations e.g., [1]
  const renderMarkdown = (content: string, citations?: any[]) => {
    // We can replace [1] with a custom component if we preprocess, 
    // or use a custom remark plugin. For simplicity, we just use a Regex replace here before passing to ReactMarkdown
    
    // Instead of complex preprocessing, we just render it. ReactMarkdown allows custom components for links.
    // However, citations are just text like [1]. 
    // A quick hack is to convert `[1]` to `[1](#citation-1)` before rendering.
    
    let processedContent = content.replace(/\[(\d+)\](?![(])/g, '[$1](#citation-$1)');

    return (
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => {
            const href = props.href || "";
            if (href.startsWith("#citation-")) {
              const idx = parseInt(href.replace("#citation-", ""));
              const citation = citations?.find((c: any) => c.id === idx);
              return (
                <button 
                  onClick={() => citation && onCitationClick(citation.doc_id)}
                  className="inline-flex items-center justify-center w-5 h-5 mx-1 text-[10px] font-bold text-white bg-[var(--accent-cyan)] rounded-full hover:bg-[var(--accent-cyan-dark)] transition-colors cursor-pointer align-middle"
                  title={citation?.filename || "Source"}
                >
                  {idx}
                </button>
              );
            }
            return <a {...props} className="text-[var(--accent-cyan)] hover:underline" />;
          }
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-primary)]">
      {/* Header */}
      <div className="h-14 border-b border-[var(--surface-border)] flex items-center px-6 shrink-0 bg-[var(--surface-glass)]">
        <h2 className="text-[16px] font-bold text-[var(--text-primary)] flex items-center gap-2">
          <Sparkles size={18} className="text-[var(--accent-cyan)]" /> AURA Research
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[var(--text-muted)] space-y-4">
            <Sparkles size={48} className="opacity-20" />
            <p>Select sources and ask a question, or use the quick actions below.</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl p-4 ${msg.role === "user" ? "bg-[var(--surface-border)] text-[var(--text-primary)]" : "bg-[var(--bg-elevated)] border border-[var(--surface-border)]"}`}>
              {msg.role === "assistant" ? (
                <div className="markdown-content text-[14px]">
                  {msg.content ? renderMarkdown(msg.content, msg.citations) : <Loader2 className="animate-spin text-[var(--accent-cyan)]" size={16} />}
                </div>
              ) : (
                <div className="text-[14px]">{msg.content}</div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <div className="px-6 py-2 flex items-center justify-center gap-2 flex-wrap shrink-0">
        <button onClick={() => handleGenerateSpecial("study_guide")} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[12px] font-medium text-[var(--text-secondary)]">
          <FileText size={14} /> Study Guide
        </button>
        <button onClick={() => handleGenerateSpecial("faq")} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[12px] font-medium text-[var(--text-secondary)]">
          <HelpCircle size={14} /> FAQ
        </button>
        <button onClick={() => handleGenerateSpecial("timeline")} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[12px] font-medium text-[var(--text-secondary)]">
          <FileClock size={14} /> Timeline
        </button>
        <button onClick={() => handleGenerateSpecial("mind_map")} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[12px] font-medium text-[var(--text-secondary)]">
          <Map size={14} /> Mind Map
        </button>
        <button onClick={() => handleGenerateSpecial("podcast")} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--surface-border)] hover:bg-[var(--surface-hover)] text-[12px] font-medium text-[var(--text-secondary)]">
          <Headphones size={14} /> Podcast Script
        </button>
      </div>

      {/* Input */}
      <div className="p-4 pt-0 shrink-0">
        <div className="relative w-full max-w-3xl mx-auto flex items-end bg-[var(--surface-glass)] border border-[var(--surface-border)] rounded-2xl overflow-hidden shadow-lg p-2 transition-all focus-within:border-[var(--accent-cyan)]">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={selectedDocIds.length > 0 ? "Ask a grounded question..." : "Select sources first..."}
            className="flex-1 max-h-[200px] min-h-[44px] bg-transparent resize-none outline-none text-[15px] p-2 overflow-y-auto"
            disabled={isGenerating || selectedDocIds.length === 0}
          />
          <button
            onClick={handleSend}
            disabled={isGenerating || !input.trim() || selectedDocIds.length === 0}
            className="shrink-0 w-10 h-10 m-1 flex items-center justify-center rounded-xl bg-[var(--accent-cyan)] text-white hover:bg-[var(--accent-cyan-dark)] disabled:opacity-50 transition-colors"
          >
            {isGenerating ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}

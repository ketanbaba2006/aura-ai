"use client";

import React from "react";
import { motion } from "framer-motion";
import { Search, Code, FileText, GraduationCap } from "lucide-react";
import type { ActiveView } from "@/types";

interface HomePageProps {
  onSendHint: (hint: string) => void;
  projectsList?: any[];
  onSwitchProject?: (id: string) => void;
  activeView?: ActiveView;
}

export function HomePage({ onSendHint, projectsList = [], onSwitchProject, activeView }: HomePageProps) {
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15, scale: 0.98 },
    show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring" as const, stiffness: 400, damping: 30 } },
  };

  const welcomeCards = [
    { label: "Create an image", icon: "🎨", query: "Create an image for me" },
    { label: "Write or edit", icon: "✍️", query: "Help me write an essay" },
    { label: "Look something up", icon: "🌐", query: "Search the web for news" },
    { label: "Analyze data", icon: "📊", query: "Analyze my dataset" }
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="w-full max-w-[768px] flex flex-col items-center px-4"
    >
      <motion.h1
        variants={itemVariants}
        className="text-[32px] font-semibold text-[var(--text-primary)] mb-8 tracking-tight text-center"
      >
        What's on the agenda today?
      </motion.h1>

      {/* Recent Projects */}
      {projectsList.length > 0 && (
        <motion.div variants={itemVariants} className="w-full mb-6">
          <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-muted)] font-bold mb-3 px-1">
            Recent Projects
          </h3>
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
            {projectsList.slice(0, 3).map((proj) => (
              <button
                key={proj.id}
                onClick={() => onSwitchProject?.(proj.id)}
                className="flex flex-col justify-center px-4 py-3 rounded-2xl min-w-[160px] text-left transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] border border-[var(--surface-border)] hover:border-[var(--text-muted)] bg-[var(--surface-glass)] outline-none shrink-0"
              >
                <span className="text-[14px] font-semibold text-[var(--text-primary)] truncate">{proj.name}</span>
                <span className="text-[12px] text-[var(--text-secondary)]">{proj.project_type || "Web Project"}</span>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Suggestion Pills */}
      <motion.div variants={itemVariants} className="flex gap-3 flex-wrap justify-center mt-2 w-full">
        {welcomeCards.map((btn, idx) => (
          <button
            key={idx}
            onClick={() => onSendHint(btn.query)}
            className="flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--surface-border)] text-[var(--text-secondary)] text-[13px] transition-all hover:bg-[var(--surface-glass)] hover:text-[var(--text-primary)] hover:scale-105 active:scale-95"
          >
            <span>{btn.icon}</span> {btn.label}
          </button>
        ))}
      </motion.div>
    </motion.div>
  );
}

"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ActiveView, Conversation } from "@/types";
import { ConversationItem } from "./ConversationItem";
import { MessageSquare, Microscope, Sparkles, Plus, Menu, LogOut, BookOpen } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuraAvatar } from "../chat/AuraAvatar";
import { AuraLogo } from "../chat/AuraLogo";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  isOpen: boolean;
  onToggle?: () => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  activeView: ActiveView;
  onSelectView: (view: ActiveView) => void;
  isOnline?: boolean;
}

export function Sidebar({
  conversations,
  activeId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  activeView,
  onSelectView,
}: SidebarProps) {
  const { user, logout } = useAuth();
  const [isHovered, setIsHovered] = useState(false);

  const topItems = [
    { view: "new" as ActiveView, icon: <Plus size={20} />, action: onNewChat, label: "New Chat" },
    { view: "chat" as ActiveView, icon: <MessageSquare size={20} />, action: () => onSelectView("chat"), label: "Chat" },
    { view: "notebook" as ActiveView, icon: <BookOpen size={20} />, action: () => onSelectView("notebook"), label: "Notebook" },
    { view: "deep-research" as ActiveView, icon: <Microscope size={20} />, action: () => onSelectView("deep-research"), label: "Deep Research" },
    { view: "agent" as ActiveView, icon: <Sparkles size={20} />, action: () => onSelectView("agent"), label: "Explore" },
  ];

  return (
    <motion.aside
      className="sidebar fixed left-0 top-0 bottom-0 flex flex-col py-4 bg-[var(--bg-primary)] z-50 overflow-hidden"
      initial={{ width: 60 }}
      animate={{ width: isHovered ? 280 : 60 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ borderRight: "none" }}
    >
      {/* ── Brand Logo Header ── */}
      <div className="shrink-0 mb-6 px-4 flex items-center cursor-pointer overflow-hidden" onClick={() => onSelectView("chat")}>
        <div className="shrink-0 flex items-center justify-center w-7 h-7">
          <AuraLogo size={28} />
        </div>
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="ml-3 flex flex-col whitespace-nowrap"
            >
              <span className="text-[14px] font-bold tracking-widest text-[var(--text-primary)]">AURA AI</span>
              <span className="text-[9px] text-[var(--text-muted)] uppercase tracking-widest font-semibold">System v2</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Navigation ── */}
      <div className="flex flex-col gap-2 w-full px-2 mb-4 shrink-0">
        {topItems.map((item, idx) => {
          const isActive = activeView === item.view;
          return (
            <button
              key={idx}
              onClick={item.action}
              className={`flex items-center w-full h-10 rounded-full transition-colors overflow-hidden ${
                isActive ? "text-[var(--text-primary)] bg-[var(--surface-glass)]" : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-glass)]"
              }`}
              title={item.label}
            >
              <div className="shrink-0 w-[44px] flex items-center justify-center">
                {item.icon}
              </div>
              <AnimatePresence>
                {isHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="whitespace-nowrap text-[13px] font-medium"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
          );
        })}
      </div>

      {/* ── Chat History ── */}
      <div className="flex-1 flex flex-col gap-1 w-full px-2 overflow-y-auto scrollbar-hide">
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[10px] font-bold tracking-[1.5px] text-[var(--text-muted)] uppercase mt-2 px-3 mb-1"
            >
              History
            </motion.div>
          )}
        </AnimatePresence>
        
        {conversations.length === 0 ? (
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="px-3 py-4 text-[var(--text-muted)] text-[12px] whitespace-nowrap"
              >
                No conversations
              </motion.div>
            )}
          </AnimatePresence>
        ) : (
          conversations.map((conv) => (
            <div key={conv.id} className={isHovered ? "w-full" : "w-10 mx-auto"}>
              <ConversationItem
                conversation={conv}
                isActive={conv.id === activeId}
                isHovered={isHovered}
                onSelect={() => onSelectConversation(conv.id)}
                onDelete={() => onDeleteConversation(conv.id)}
              />
            </div>
          ))
        )}
      </div>

      {/* ── Bottom Section ── */}
      <div className="flex flex-col gap-2 w-full px-2 mt-4 shrink-0">
        <button
          onClick={() => onSelectView("projects")}
          className="flex items-center w-full h-10 rounded-full transition-colors text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-glass)] overflow-hidden"
          title="Menu"
        >
          <div className="shrink-0 w-[44px] flex items-center justify-center">
            <Menu size={20} />
          </div>
          <AnimatePresence>
            {isHovered && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="whitespace-nowrap text-[13px] font-medium"
              >
                Projects
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {user && (
          <div className="flex flex-col gap-2">
            <button
              onClick={() => onSelectView("settings")}
              className="flex items-center w-full h-10 rounded-full transition-colors hover:bg-[var(--surface-glass)] overflow-hidden"
              title="Profile"
            >
              <div className="shrink-0 w-[44px] flex items-center justify-center">
                <AuraAvatar size={28} state="idle" />
              </div>
              <AnimatePresence>
                {isHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="whitespace-nowrap text-[13px] font-medium text-[var(--text-primary)]"
                  >
                    Settings
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
            <AnimatePresence>
              {isHovered && (
                <motion.button
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "40px" }}
                  exit={{ opacity: 0, height: 0 }}
                  onClick={logout}
                  className="flex items-center w-full rounded-full transition-colors text-red-400 hover:bg-red-500/10 hover:text-red-300 overflow-hidden"
                >
                  <div className="shrink-0 w-[44px] flex items-center justify-center">
                    <LogOut size={18} />
                  </div>
                  <span className="whitespace-nowrap text-[13px] font-medium">Log out</span>
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.aside>
  );
}

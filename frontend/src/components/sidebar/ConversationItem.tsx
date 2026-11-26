/**
 * AURA AI Conversation Item
 * Single conversation entry in the sidebar.
 */

"use client";

import type { Conversation } from "@/types";
import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare, X } from "lucide-react";

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  isHovered: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export function ConversationItem({
  conversation,
  isActive,
  isHovered,
  onSelect,
  onDelete,
}: ConversationItemProps) {
  return (
    <div
      onClick={onSelect}
      className={`flex items-center gap-3 p-2 rounded-lg transition-all duration-200 cursor-pointer relative group ${
        isActive 
          ? "bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] text-[#EDEDED]" 
          : "text-[#A1A1AA] hover:bg-[rgba(255,255,255,0.03)] hover:text-[#EDEDED] border border-transparent"
      } ${!isHovered ? "justify-center opacity-50 hover:opacity-100" : ""}`}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect();
      }}
    >
      <div className="shrink-0 w-5 h-5 flex items-center justify-center">
        <MessageSquare size={14} className={isActive ? "text-[#A8FF00]" : ""} />
      </div>

      <AnimatePresence>
        {isHovered && (
          <>
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis flex-1 pr-6"
            >
              {conversation.title}
            </motion.span>
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[#A1A1AA] hover:text-red-400 hover:bg-red-400/10 rounded opacity-0 group-hover:opacity-100 transition-all"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              title="Delete"
            >
              <X size={14} />
            </motion.button>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * AURA AI Notification Context
 * Toast and Modal management using Framer Motion & premium glassmorphism styles.
 */

"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export interface ModalAction {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "danger";
}

export interface ModalOptions {
  title: string;
  description: string;
  content?: ReactNode;
  actions: ModalAction[];
}

interface NotificationContextProps {
  showToast: (message: string, type?: ToastType) => void;
  showModal: (options: ModalOptions) => void;
  closeModal: () => void;
}

const NotificationContext = createContext<NotificationContextProps | undefined>(undefined);

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotification must be used within a NotificationProvider");
  }
  return context;
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [modal, setModal] = useState<ModalOptions | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const showModal = useCallback((options: ModalOptions) => {
    setModal(options);
    setIsModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <NotificationContext.Provider value={{ showToast, showModal, closeModal }}>
      {children}

      {/* Toasts Container */}
      <div
        style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          maxWidth: "360px",
          width: "100%",
          pointerEvents: "none",
        }}
      >
        
          {toasts.map((toast) => {
            const icon =
              toast.type === "success" ? (
                <CheckCircle size={16} style={{ color: "#34d399" }} />
              ) : toast.type === "error" ? (
                <AlertCircle size={16} style={{ color: "#f87171" }} />
              ) : (
                <Info size={16} style={{ color: "var(--accent-cyan)" }} />
              );

            const glowColor =
              toast.type === "success"
                ? "rgba(52, 211, 153, 0.15)"
                : toast.type === "error"
                ? "rgba(248, 113, 113, 0.15)"
                : "rgba(6, 214, 214, 0.15)";

            const borderColor =
              toast.type === "success"
                ? "rgba(52, 211, 153, 0.2)"
                : toast.type === "error"
                ? "rgba(248, 113, 113, 0.2)"
                : "rgba(6, 214, 214, 0.2)";

            return (
              <div
                key={toast.id}
                style={{
                  pointerEvents: "auto",
                  background: "rgba(10, 10, 18, 0.85)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: `1px solid ${borderColor}`,
                  borderRadius: "14px",
                  padding: "12px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  boxShadow: `0 8px 32px rgba(0, 0, 0, 0.4), 0 0 16px ${glowColor}`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
                  {icon}
                </div>
                <div
                  style={{
                    color: "var(--text-primary)",
                    fontSize: "13px",
                    fontWeight: "500",
                    flex: 1,
                    lineHeight: "1.4",
                  }}
                >
                  {toast.message}
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "2px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    opacity: 0.7,
                    outline: "none",
                    transition: "opacity var(--transition-fast)",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.7")}
                >
                  <X size={14} />
                </button>
              </div>
            );
          })}
        
      </div>

      {/* Modal Dialog */}
      
        {isModalOpen && modal && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 99999,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "20px",
            }}
          >
            {/* Backdrop */}
            <div
              onClick={closeModal}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: "rgba(0, 0, 0, 0.65)",
                backdropFilter: "blur(4px)",
                WebkitBackdropFilter: "blur(4px)",
              }}
            />

            {/* Modal Card */}
            <div
              style={{
                position: "relative",
                background: "rgba(10, 10, 18, 0.9)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "20px",
                width: "100%",
                maxWidth: "480px",
                padding: "24px",
                boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6), 0 0 32px rgba(6, 214, 214, 0.05)",
                zIndex: 1,
              }}
            >
              {/* Close Button */}
              <button
                onClick={closeModal}
                style={{
                  position: "absolute",
                  top: "20px",
                  right: "20px",
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "4px",
                  opacity: 0.6,
                  outline: "none",
                  transition: "opacity var(--transition-fast)",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.6")}
              >
                <X size={16} />
              </button>

              {/* Title */}
              <h2
                style={{
                  fontSize: "18px",
                  fontWeight: "700",
                  color: "var(--text-primary)",
                  marginBottom: "8px",
                  letterSpacing: "-0.3px",
                }}
              >
                {modal.title}
              </h2>

              {/* Description */}
              <p
                style={{
                  fontSize: "14px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.5",
                  marginBottom: modal.content ? "16px" : "24px",
                }}
              >
                {modal.description}
              </p>

              {/* Custom Content JSX */}
              {modal.content && (
                <div style={{ marginBottom: "24px" }}>
                  {modal.content}
                </div>
              )}

              {/* Actions Grid */}
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  justifyContent: "flex-end",
                  width: "100%",
                }}
              >
                {modal.actions.map((act, index) => {
                  const isPrimary = act.variant === "primary";
                  const isDanger = act.variant === "danger";
                  
                  let bg = "rgba(255, 255, 255, 0.03)";
                  let border = "1px solid rgba(255, 255, 255, 0.05)";
                  let color = "var(--text-primary)";
                  let glow = "none";

                  if (isPrimary) {
                    bg = "rgba(6, 214, 214, 0.05)";
                    border = "1px solid rgba(6, 214, 214, 0.15)";
                    color = "var(--accent-cyan)";
                    glow = "0 0 12px rgba(6, 214, 214, 0.1)";
                  } else if (isDanger) {
                    bg = "rgba(239, 68, 68, 0.08)";
                    border = "1px solid rgba(239, 68, 68, 0.2)";
                    color = "#f87171";
                    glow = "0 0 12px rgba(239, 68, 68, 0.15)";
                  }

                  return (
                    <button
                      key={index}
                      onClick={() => {
                        act.onClick();
                        closeModal();
                      }}
                      style={{
                        padding: "10px 18px",
                        borderRadius: "10px",
                        background: bg,
                        border: border,
                        color: color,
                        fontSize: "13px",
                        fontWeight: "600",
                        cursor: "pointer",
                        transition: "all var(--transition-fast)",
                        boxShadow: glow,
                        outline: "none",
                      }}
                      onMouseEnter={(e) => {
                        if (isPrimary) {
                          e.currentTarget.style.background = "rgba(6, 214, 214, 0.1)";
                          e.currentTarget.style.boxShadow = "0 0 16px rgba(6, 214, 214, 0.25)";
                        } else if (isDanger) {
                          e.currentTarget.style.background = "rgba(239, 68, 68, 0.15)";
                          e.currentTarget.style.boxShadow = "0 0 16px rgba(239, 68, 68, 0.35)";
                        } else {
                          e.currentTarget.style.background = "rgba(255, 255, 255, 0.07)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = bg;
                        e.currentTarget.style.boxShadow = glow;
                      }}
                    >
                      {act.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      
    </NotificationContext.Provider>
  );
}

/**
 * AURA OS Goal Planner Dashboard Page
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import type { Goal, Task } from "@/types";
import { useNotification } from "@/context/NotificationContext";
import { fetchWithAuth } from "@/lib/api";

export function PlannerPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [goalInput, setGoalInput] = useState("");
  const [descInput, setDescInput] = useState("");
  const [isDecomposing, setIsDecomposing] = useState(false);
  const [isLoadingGoals, setIsLoadingGoals] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showToast, showModal } = useNotification();

  const fetchGoals = useCallback(async (selectId?: string) => {
    setIsLoadingGoals(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/planner/goals`);
      if (resp.ok) {
        const data = await resp.json();
        setGoals(data);
        
        // Auto select first goal if none selected
        if (data.length > 0) {
          const toSelect = selectId ? data.find((g: Goal) => g.id === selectId) : data[0];
          if (toSelect) {
            await fetchGoalDetails(toSelect.id);
          }
        } else {
          setSelectedGoal(null);
        }
      }
    } catch (e) {
      console.error("Failed to load goals", e);
    } finally {
      setIsLoadingGoals(false);
    }
  }, []);

  const fetchGoalDetails = async (goalId: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/planner/goals/${goalId}`);
      if (resp.ok) {
        const data = await resp.json();
        setSelectedGoal(data);
      }
    } catch (e) {
      console.error("Failed to load goal details", e);
    }
  };

  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);

  const handleDecompose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalInput.trim()) return;

    setIsDecomposing(true);
    setError(null);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/planner/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: goalInput, description: descInput }),
      });

      if (!resp.ok) {
        throw new Error("Failed to decompose goal into tasks.");
      }

      const newGoalDetails = await resp.json();
      setGoalInput("");
      setDescInput("");
      
      // Reload goals list and select the new one
      await fetchGoals(newGoalDetails.id);
    } catch (err: any) {
      setError(err.message || "Failed to decompose goal.");
    } finally {
      setIsDecomposing(false);
    }
  };

  const handleToggleTask = async (task: Task) => {
    if (!selectedGoal) return;
    const nextStatus = task.status === "completed" ? "pending" : "completed";

    // Optimistically update UI
    const updatedTasks = selectedGoal.tasks?.map((t) =>
      t.id === task.id ? { ...t, status: nextStatus } : t
    ) as Task[];
    setSelectedGoal({ ...selectedGoal, tasks: updatedTasks });

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/planner/tasks/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });

      if (!resp.ok) throw new Error("Status sync failed.");
      
      // Refresh list to update overall status (completed / pending)
      await fetchGoals(selectedGoal.id);
    } catch (e) {
      console.error("Failed to update task status", e);
      // Revert optimistic update
      fetchGoalDetails(selectedGoal.id);
    }
  };

  const handleDeleteGoal = (id: string) => {
    showModal({
      title: "Confirm Delete Goal",
      description: "Are you sure you want to delete this goal and all tasks?",
      actions: [
        {
          label: "Delete Goal",
          variant: "danger",
          onClick: () => executeDeleteGoal(id)
        },
        {
          label: "Cancel",
          variant: "secondary",
          onClick: () => {}
        }
      ]
    });
  };

  const executeDeleteGoal = async (id: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const resp = await fetchWithAuth(`${apiBase}/planner/goals/${id}`, { method: "DELETE" });
      if (resp.ok) {
        await fetchGoals();
        showToast("Goal successfully deleted.", "success");
      } else {
        showToast("Failed to delete goal.", "error");
      }
    } catch (e) {
      showToast("Error deleting goal.", "error");
      console.error("Delete goal failed", e);
    }
  };

  return (
    <div className="page-container" style={{ padding: "40px", height: "100%", overflowY: "auto" }}>
      <div className="page-header" style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "600", color: "var(--text)", marginBottom: "8px" }}>
          📋 Planner Engine
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
          Input project goals. AURA decomposes them into structured checklists of sub-tasks.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
        {/* Left column: Goals List & Form */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Decompose Goal Form */}
          <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)" }}>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Initialize New Goal</h2>
            
            <form onSubmit={handleDecompose} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <input
                type="text"
                className="chat-input-field"
                placeholder="What is the high-level goal? (e.g. Build a portfolio page)"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  outline: "none",
                  fontSize: "14px"
                }}
              />
              <textarea
                placeholder="Optionally add specific details or guidelines to help planner..."
                value={descInput}
                onChange={(e) => setDescInput(e.target.value)}
                rows={3}
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  outline: "none",
                  fontSize: "14px",
                  resize: "none"
                }}
              />
              <button
                type="submit"
                disabled={isDecomposing}
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  background: "var(--primary)",
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: "600",
                  fontSize: "14px"
                }}
              >
                {isDecomposing ? "Decomposing into tasks..." : "Decompose Goal"}
              </button>
            </form>

            {error && (
              <div style={{ marginTop: "16px", padding: "12px", borderRadius: "6px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--error)", color: "var(--error)", fontSize: "13px" }}>
                {error}
              </div>
            )}
          </div>

          {/* Goals catalog Card */}
          <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", flex: 1 }}>
            <h2 style={{ fontSize: "18px", color: "var(--text)", marginBottom: "16px" }}>Active Projects</h2>

            {isLoadingGoals ? (
              <div style={{ color: "var(--text-muted)", padding: "20px", textAlign: "center", fontSize: "14px" }}>Loading catalogue...</div>
            ) : goals.length === 0 ? (
              <div style={{ color: "var(--text-muted)", padding: "40px", textAlign: "center", fontSize: "14px" }}>
                No goals created yet. Submit a goal to decompose.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "400px", overflowY: "auto" }}>
                {goals.map((g) => (
                  <div
                    key={g.id}
                    onClick={() => fetchGoalDetails(g.id)}
                    style={{
                      padding: "14px 18px",
                      borderRadius: "8px",
                      background: selectedGoal?.id === g.id ? "rgba(255, 255, 255, 0.05)" : "rgba(255,255,255,0.01)",
                      border: `1px solid ${selectedGoal?.id === g.id ? "var(--primary)" : "var(--border)"}`,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      cursor: "pointer"
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <span style={{ color: "var(--text)", fontSize: "14px", fontWeight: "500" }}>{g.title}</span>
                      <span style={{
                        fontSize: "11px",
                        color: g.status === "completed" ? "#34d399" : g.status === "in_progress" ? "#fbbf24" : "var(--text-muted)",
                        fontWeight: "600",
                        textTransform: "uppercase"
                      }}>
                        {g.status.replace("_", " ")}
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteGoal(g.id);
                      }}
                      style={{
                        padding: "4px 8px",
                        borderRadius: "4px",
                        background: "rgba(239, 68, 68, 0.08)",
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

        {/* Right column: Task checklist inspector */}
        <div className="chat-card" style={{ padding: "24px", borderRadius: "12px", background: "var(--card)", border: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
          {selectedGoal ? (
            <>
              <div style={{ marginBottom: "20px" }}>
                <h2 style={{ fontSize: "20px", color: "var(--text)", fontWeight: "600", marginBottom: "6px" }}>{selectedGoal.title}</h2>
                <p style={{ color: "var(--text-muted)", fontSize: "13.5px", lineHeight: "1.4" }}>
                  {selectedGoal.description || "No description details provided."}
                </p>
              </div>

              <h3 style={{ fontSize: "14px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>Decomposed Checklist</h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "12px", flex: 1, overflowY: "auto" }}>
                {selectedGoal.tasks?.map((task) => (
                  <div
                    key={task.id}
                    style={{
                      padding: "16px",
                      borderRadius: "8px",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid var(--border)",
                      display: "flex",
                      gap: "14px",
                      alignItems: "flex-start",
                      opacity: task.status === "completed" ? 0.6 : 1
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={task.status === "completed"}
                      onChange={() => handleToggleTask(task)}
                      style={{
                        width: "18px",
                        height: "18px",
                        borderRadius: "4px",
                        border: "1px solid var(--border)",
                        cursor: "pointer",
                        accentColor: "var(--primary)",
                        marginTop: "2px"
                      }}
                    />
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <span style={{
                        color: "var(--text)",
                        fontSize: "14px",
                        fontWeight: "500",
                        textDecoration: task.status === "completed" ? "line-through" : "none"
                      }}>
                        {task.title}
                      </span>
                      {task.description && (
                        <span style={{ color: "var(--text-muted)", fontSize: "12px", lineHeight: "1.4" }}>
                          {task.description}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "14px", padding: "80px" }}>
              Select a project on the left to inspect tasks.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

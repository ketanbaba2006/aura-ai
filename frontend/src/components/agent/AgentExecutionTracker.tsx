'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2, Circle, AlertCircle } from 'lucide-react';

export type AgentTaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface AgentTask {
  id: string;
  name: string;
  status: AgentTaskStatus;
  detail?: string;
}

interface AgentExecutionTrackerProps {
  tasks: AgentTask[];
  title?: string;
}

export function AgentExecutionTracker({ tasks, title = "Agent Execution Pipeline" }: AgentExecutionTrackerProps) {
  if (!tasks || tasks.length === 0) return null;

  const [isExpanded, setIsExpanded] = React.useState(true);
  const activeTaskCount = tasks.filter(t => t.status === 'running' || t.status === 'pending').length;

  return (
    <div className="agent-tracker" style={{
      background: 'var(--surface-glass)',
      border: '1px solid var(--surface-border)',
      borderRadius: '16px',
      padding: '20px 24px',
      width: '100%',
      maxWidth: '600px',
      margin: '0 auto',
      position: 'relative',
      overflow: 'hidden',
      transition: 'all 0.3s ease'
    }}>
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <h3 style={{
          fontSize: '13px',
          fontWeight: '700',
          color: 'var(--accent-cyan)',
          textTransform: 'uppercase',
          letterSpacing: '1.5px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          margin: 0
        }}>
          {activeTaskCount > 0 ? (
            <Loader2 size={14} className="animate-spin" color="var(--accent-cyan)" />
          ) : (
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-cyan)' }} />
          )}
          {title}
        </h3>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {isExpanded ? 'Hide' : 'Show'}
        </span>
      </div>

      <motion.div 
        initial={false}
        animate={{ height: isExpanded ? 'auto' : 0, opacity: isExpanded ? 1 : 0, marginTop: isExpanded ? '20px' : 0 }}
        style={{ overflow: 'hidden' }}
      >
        <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', gap: '0' }}>
        {tasks.map((task, index) => {
          const isLast = index === tasks.length - 1;
          const isActive = task.status === 'running';
          const isCompleted = task.status === 'completed';
          const isFailed = task.status === 'failed';

          let iconColor = 'var(--text-muted)';
          if (isActive) iconColor = 'var(--accent-cyan)';
          if (isCompleted) iconColor = 'var(--accent-green)';
          if (isFailed) iconColor = 'var(--error)';

          return (
            <div key={task.id} style={{ display: 'flex', gap: '16px', position: 'relative' }}>
              {/* Connector Line */}
              {!isLast && (
                <div style={{
                  position: 'absolute',
                  left: '11px',
                  top: '24px',
                  bottom: '-12px',
                  width: '2px',
                  background: isCompleted ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)',
                  boxShadow: isCompleted ? '0 0 10px var(--accent-green)' : 'none',
                  zIndex: 0
                }}>
                  {/* Energy pulse traveling down the line */}
                  {isActive && (
                    <motion.div
                      style={{
                        width: '100%',
                        height: '30%',
                        background: 'linear-gradient(to bottom, transparent, var(--accent-cyan), transparent)',
                        boxShadow: 'var(--glow-cyan)'
                      }}
                      animate={{ y: ['-100%', '300%'] }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                    />
                  )}
                </div>
              )}

              {/* Node Icon */}
              <div style={{
                position: 'relative',
                zIndex: 1,
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: 'var(--bg-surface)',
                border: `2px solid ${iconColor}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginTop: '2px',
                boxShadow: isActive || isCompleted ? `0 0 15px ${iconColor}` : 'none',
                transition: 'all var(--transition-normal)'
              }}>
                {isCompleted ? <Check size={12} color={iconColor} /> :
                 isActive ? <Loader2 size={12} color={iconColor} className="animate-spin" /> :
                 isFailed ? <AlertCircle size={12} color={iconColor} /> :
                 <Circle size={8} fill={iconColor} color={iconColor} />}
              </div>

              {/* Content */}
              <div style={{
                flex: 1,
                paddingBottom: isLast ? '0' : '24px',
                opacity: task.status === 'pending' ? 0.5 : 1,
                transition: 'opacity var(--transition-normal)'
              }}>
                <div style={{
                  fontSize: '14px',
                  fontWeight: isActive || isCompleted ? '600' : '500',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)'
                }}>
                  {task.name}
                </div>
                
                {task.detail && (
                  <motion.div 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    style={{
                      marginTop: '6px',
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      fontFamily: '"SF Mono", "Fira Code", monospace',
                      background: 'rgba(0,0,0,0.3)',
                      padding: '8px',
                      borderRadius: '8px',
                      border: '1px solid rgba(255,255,255,0.02)'
                    }}
                  >
                    {task.detail}
                  </motion.div>
                )}
              </div>
            </div>
          );
        })}
        </div>
      </motion.div>
    </div>
  );
}

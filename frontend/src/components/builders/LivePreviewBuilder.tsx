'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Code2, Monitor, Loader2, Play, RefreshCw, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { LiveSandbox } from '../sandbox/LiveSandbox';

interface LivePreviewBuilderProps {
  type: 'website' | 'app';
  initialPrompt?: string;
}

export function LivePreviewBuilder({ type, initialPrompt = '' }: LivePreviewBuilderProps) {
  const [isBuilding, setIsBuilding] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [codeContent, setCodeContent] = useState(`import React from 'react';
import { motion } from 'framer-motion';

export default function App() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white font-sans">
      <motion.div 
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="p-8 bg-gray-800 rounded-2xl shadow-2xl text-center"
      >
        <h1 className="text-4xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-500">
          AURA Generated App
        </h1>
        <p className="text-gray-400">Powered by LiveSandbox Rendering Engine</p>
      </motion.div>
    </div>
  );
}`);
  
  const handleBuild = () => {
    setIsBuilding(true);
    // Mandatory 15-second "loading/compilation" delay during website/app generation
    setTimeout(() => {
      setIsBuilding(false);
      setShowPreview(true);
    }, 15000);
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>
      
      {/* Left Panel - Chat / Commands */}
      <motion.div 
        initial={false}
        animate={{ width: sidebarOpen ? 400 : 0, opacity: sidebarOpen ? 1 : 0 }}
        style={{
          borderRight: '1px solid var(--surface-border)',
          background: 'rgba(6,6,12,0.8)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 10,
          overflow: 'hidden'
        }}
      >
        <div style={{ width: '400px', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{
          padding: '20px',
          borderBottom: '1px solid var(--surface-border)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{ padding: '8px', background: 'var(--surface-glass)', borderRadius: '8px' }}>
            {type === 'website' ? <Monitor size={20} color="var(--accent-cyan)" /> : <Code2 size={20} color="var(--accent-purple)" />}
          </div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {type === 'website' ? 'Website Builder' : 'App Builder'}
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Powered by AURA OS Engine</p>
          </div>
        </div>

        <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{
            background: 'var(--surface-glass)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--surface-border)',
            fontSize: '13px',
            color: 'var(--text-secondary)',
            lineHeight: '1.6'
          }}>
            Welcome to the {type === 'website' ? 'Website' : 'App'} Builder. Describe what you want to create, and I will generate the complete project for you.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'auto' }}>
            <textarea 
              placeholder={`Describe your ${type}...`}
              style={{
                width: '100%',
                minHeight: '100px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--surface-border)',
                borderRadius: '12px',
                padding: '12px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                resize: 'none',
                outline: 'none',
                transition: 'border-color var(--transition-fast)'
              }}
              defaultValue={initialPrompt}
              onFocus={(e) => { e.target.style.borderColor = 'var(--accent-cyan)'; }}
              onBlur={(e) => { e.target.style.borderColor = 'var(--surface-border)'; }}
            />
            <button
              onClick={handleBuild}
              disabled={isBuilding}
              style={{
                width: '100%',
                padding: '12px',
                background: isBuilding ? 'var(--surface-glass)' : 'var(--accent-gradient)',
                color: isBuilding ? 'var(--text-muted)' : 'var(--bg-primary)',
                border: 'none',
                borderRadius: '12px',
                fontWeight: '700',
                cursor: isBuilding ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all var(--transition-normal)',
                boxShadow: isBuilding ? 'none' : 'var(--glow-cyan)'
              }}
            >
              {isBuilding ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Build {type === 'website' ? 'Website' : 'App'}
                </>
              )}
            </button>
          </div>
        </div>
        </div>
      </motion.div>
      {/* Right Panel - Live Preview / Code */}
      <div style={{ flex: 1, background: 'var(--bg-primary)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        
        {/* Top Bar */}
        <div style={{
          height: '48px',
          borderBottom: '1px solid var(--surface-border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: '16px',
          background: 'rgba(10,10,15,0.8)'
        }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '4px',
                marginRight: '8px'
              }}
            >
              {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444' }} />
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b' }} />
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981' }} />
          </div>
          
          <div style={{
            flex: 1,
            display: 'flex',
            justifyContent: 'center'
          }}>
            <div style={{
              background: 'var(--bg-surface)',
              padding: '4px 24px',
              borderRadius: '20px',
              fontSize: '12px',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              localhost:3000
              <RefreshCw size={12} style={{ cursor: 'pointer' }} />
            </div>
          </div>
        </div>

        {/* Preview Area */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {isBuilding ? (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '24px' }}>
              <div style={{ position: 'relative' }}>
                <div style={{ width: '80px', height: '80px', borderRadius: '50%', border: '2px solid var(--surface-border)', borderTopColor: 'var(--accent-cyan)', animation: 'spin 1s linear infinite' }} />
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Code2 size={24} color="var(--accent-cyan)" />
                </div>
              </div>
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{ textAlign: 'center' }}
              >
                <h3 style={{ fontSize: '18px', color: 'var(--text-primary)', marginBottom: '8px' }}>Compiling Application</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Setting up React components and styles...</p>
              </motion.div>
            </div>
          ) : showPreview ? (
            <div style={{ width: '100%', height: '100%', background: '#050508' }}>
              <LiveSandbox 
                name={type === 'website' ? 'index.html' : 'App.tsx'}
                path={type === 'website' ? 'temp/index.html' : 'temp/App.tsx'}
                content={codeContent}
                onChange={setCodeContent}
                isTemporary={true}
              />
            </div>
          ) : (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              <div style={{ textAlign: 'center' }}>
                <Monitor size={48} style={{ opacity: 0.2, margin: '0 auto 16px' }} />
                <p>Preview will appear here</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

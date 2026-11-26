'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { AuraAvatar } from './AuraAvatar';

export function AuraThinkingState() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '32px 16px',
        gap: '20px',
      }}
    >
      <AuraAvatar state="thinking" size={72} />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '12px',
          fontWeight: '600',
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: 'rgba(168, 255, 0, 0.7)',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        <span>AURA is thinking</span>
        <motion.span
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          •••
        </motion.span>
      </motion.div>
    </div>
  );
}

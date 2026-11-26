'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface AuraLogoProps {
  size?: number;
  className?: string;
  animate?: boolean;
  glowIntensity?: 'low' | 'medium' | 'high';
}

export function AuraLogo({ size = 40, className = "", animate = false, glowIntensity = 'low' }: AuraLogoProps) {
  const glowMap = {
    low: '0 0 15px rgba(168, 255, 0, 0.3), 0 0 30px rgba(168, 255, 0, 0.1)',
    medium: '0 0 20px rgba(168, 255, 0, 0.5), 0 0 40px rgba(168, 255, 0, 0.2), 0 0 60px rgba(0, 255, 200, 0.1)',
    high: '0 0 25px rgba(168, 255, 0, 0.7), 0 0 50px rgba(168, 255, 0, 0.4), 0 0 80px rgba(0, 255, 200, 0.2), 0 0 120px rgba(168, 255, 0, 0.1)',
  };

  return (
    <motion.div
      className={className}
      style={{
        width: size,
        height: size,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        perspective: '600px',
      }}
      animate={
        animate
          ? {
              rotateY: [-6, 6, -6],
              rotateX: [3, -3, 3],
            }
          : {}
      }
      transition={{
        duration: 6,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      {/* Circular container with backside glow */}
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          overflow: 'hidden',
          position: 'relative',
          boxShadow: glowMap[glowIntensity],
          border: '1.5px solid rgba(168, 255, 0, 0.15)',
          background: 'radial-gradient(circle at 50% 50%, rgba(168, 255, 0, 0.06) 0%, rgba(0, 0, 0, 0.9) 70%)',
        }}
      >
        <img
          src="/aura-logo.png"
          alt="AURA AI Logo"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
          }}
        />
      </div>
    </motion.div>
  );
}

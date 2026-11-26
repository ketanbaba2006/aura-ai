'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AuraParticleField } from './AuraParticleField';

import type { AuraState } from "@/types";

interface AuraAvatarProps {
  state?: AuraState;
  size?: number;
  className?: string;
}

/**
 * AURA AI Core — The living alien-tech avatar.
 * 5 distinct behavioral states with independent ring rotations,
 * energy particles, pulse waves, and orbiting dots.
 */
export function AuraAvatar({ state = 'idle', size = 48, className = "" }: AuraAvatarProps) {

  // ── Glow intensity per state ──
  const glowStyles: Record<AuraState, string> = {
    idle:        '0 0 12px rgba(168, 255, 0, 0.15), 0 0 25px rgba(168, 255, 0, 0.06)',
    thinking:    '0 0 20px rgba(168, 255, 0, 0.4), 0 0 45px rgba(168, 255, 0, 0.15), 0 0 70px rgba(0, 255, 200, 0.08)',
    generating:  '0 0 30px rgba(168, 255, 0, 0.6), 0 0 60px rgba(168, 255, 0, 0.3), 0 0 100px rgba(0, 255, 200, 0.15)',
    researching: '0 0 25px rgba(0, 255, 200, 0.5), 0 0 50px rgba(0, 255, 200, 0.2), 0 0 80px rgba(168, 255, 0, 0.1)',
    agent:       '0 0 35px rgba(168, 255, 0, 0.7), 0 0 70px rgba(168, 255, 0, 0.35), 0 0 120px rgba(0, 255, 200, 0.2)',
    planning:    '0 0 25px rgba(167, 139, 250, 0.5), 0 0 50px rgba(167, 139, 250, 0.2)',
    building:    '0 0 25px rgba(251, 191, 36, 0.5), 0 0 50px rgba(251, 191, 36, 0.2)',
    deploying:   '0 0 25px rgba(244, 63, 94, 0.5), 0 0 50px rgba(244, 63, 94, 0.2)',
    success:     '0 0 25px rgba(52, 211, 153, 0.5), 0 0 50px rgba(52, 211, 153, 0.2)',
    error:       '0 0 25px rgba(248, 113, 113, 0.5), 0 0 50px rgba(248, 113, 113, 0.2)',
  };

  // ── Logo 3D motion per state ──
  const logoVariants = {
    idle: {
      scale: [1, 1.025, 1],
      y: [0, -2, 0],
      rotateY: [-3, 3, -3],
      rotateX: [1, -1, 1],
      transition: { duration: 5, repeat: Infinity, ease: 'easeInOut' },
    },
    thinking: {
      scale: [1, 1.05, 1],
      y: [0, -4, 0],
      rotateY: [-10, 10, -10],
      rotateX: [5, -5, 5],
      transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' },
    },
    generating: {
      scale: [1.02, 1.08, 1.02],
      y: [0, -2, 0],
      rotateY: [-15, 15, -15],
      rotateX: [6, -6, 6],
      transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
    },
    researching: {
      scale: [1, 1.04, 1],
      y: [0, -3, 0],
      rotateY: [-6, 6, -6],
      rotateZ: [-2, 2, -2],
      transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
    },
    agent: {
      scale: [1.03, 1.1, 1.03],
      y: [0, -3, 0],
      rotateY: [-20, 20, -20],
      rotateX: [8, -8, 8],
      transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
    },
    planning: {
      scale: [1.02, 1.08, 1.02],
      y: [0, -2, 0],
      rotateY: [-15, 15, -15],
      rotateX: [6, -6, 6],
      transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
    },
    building: {
      scale: [1.03, 1.1, 1.03],
      y: [0, -3, 0],
      rotateY: [-20, 20, -20],
      rotateX: [8, -8, 8],
      transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
    },
    deploying: {
      scale: [1.05, 1.15, 1.05],
      y: [0, -4, 0],
      rotateY: [-25, 25, -25],
      rotateX: [10, -10, 10],
      transition: { duration: 1, repeat: Infinity, ease: 'easeInOut' },
    },
    success: {
      scale: [1, 1.05, 1],
      y: [0, 0, 0],
      rotateY: [0, 360],
      transition: { duration: 2, repeat: 1, ease: 'easeInOut' },
    },
    error: {
      scale: [1, 0.95, 1],
      x: [-5, 5, -5, 5, 0],
      transition: { duration: 0.5, repeat: 1, ease: 'easeInOut' },
    },
  };

  // ── Ring configurations ──
  const ringConfigs = {
    idle:        [{ show: true,  speed: 30,  dir: 1, opacity: 0.08, dash: true,  scale: 1.3  }],
    thinking:    [
      { show: true, speed: 8, dir: 1, opacity: 0.4, dash: true, scale: 1.35 },
      { show: true, speed: 6, dir: -1, opacity: 0.25, dash: false, scale: 1.2 },
    ],
    generating:  [
      { show: true, speed: 3, dir: 1, opacity: 0.7, dash: true, scale: 1.4 },
      { show: true, speed: 2, dir: -1, opacity: 0.5, dash: false, scale: 1.25 },
    ],
    researching: [
      { show: true, speed: 10, dir: 1, opacity: 0.35, dash: true, scale: 1.3 },
      { show: true, speed: 7, dir: -1, opacity: 0.2, dash: false, scale: 1.15 },
    ],
    agent:       [
      { show: true, speed: 4, dir: 1, opacity: 0.6, dash: true, scale: 1.45 },
      { show: true, speed: 3, dir: -1, opacity: 0.4, dash: false, scale: 1.3 },
      { show: true, speed: 5, dir: 1, opacity: 0.25, dash: true, scale: 1.15 },
    ],
    planning: [
      { show: true, speed: 3, dir: 1, opacity: 0.7, dash: true, scale: 1.4 },
      { show: true, speed: 2, dir: -1, opacity: 0.5, dash: false, scale: 1.25 },
    ],
    building: [
      { show: true, speed: 4, dir: 1, opacity: 0.6, dash: true, scale: 1.45 },
      { show: true, speed: 3, dir: -1, opacity: 0.4, dash: false, scale: 1.3 },
      { show: true, speed: 5, dir: 1, opacity: 0.25, dash: true, scale: 1.15 },
    ],
    deploying: [
      { show: true, speed: 2, dir: 1, opacity: 0.8, dash: true, scale: 1.5 },
      { show: true, speed: 1.5, dir: -1, opacity: 0.6, dash: false, scale: 1.35 },
      { show: true, speed: 3, dir: 1, opacity: 0.4, dash: true, scale: 1.2 },
    ],
    success: [
      { show: true, speed: 10, dir: 1, opacity: 0.5, dash: false, scale: 1.3 },
    ],
    error: [
      { show: true, speed: 20, dir: -1, opacity: 0.5, dash: true, scale: 1.2 },
    ],
  };

  const rings = ringConfigs[state] || ringConfigs['idle'];
  const showParticles = state !== 'idle' && state !== 'success' && state !== 'error';
  const particleMode = state === 'researching' ? 'orbit' : 'spiral';
  const particleDensity = state === 'agent' ? 50 : state === 'generating' ? 40 : 20;
  const numDots = state === 'agent' ? 6 : state === 'generating' ? 4 : state === 'thinking' ? 3 : 0;
  const borderOpacity = state === 'agent' ? 0.35 : state === 'generating' ? 0.3 : state === 'thinking' ? 0.2 : 0.08;

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* ── Pulse wave ── */}
      <AnimatePresence>
        {state !== 'idle' && (
          <motion.div
            key="pulse"
            initial={{ scale: 1, opacity: 0 }}
            animate={{
              scale: [1, 1.8, 2.2],
              opacity: [state === 'generating' ? 0.5 : 0.3, 0.1, 0],
            }}
            transition={{ duration: state === 'generating' ? 1 : 2, repeat: Infinity, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              width: size,
              height: size,
              borderRadius: '50%',
              border: '1.5px solid rgba(168, 255, 0, 0.4)',
              pointerEvents: 'none',
            }}
          />
        )}
      </AnimatePresence>

      {/* ── Rotating rings ── */}
      {rings.map((ring, i) => (
        <motion.div
          key={`ring-${state}-${i}`}
          animate={{ rotate: ring.dir > 0 ? 360 : -360 }}
          transition={{ duration: ring.speed, repeat: Infinity, ease: 'linear' }}
          style={{
            position: 'absolute',
            width: size * ring.scale,
            height: size * ring.scale,
            borderRadius: '50%',
            border: `${ring.dash ? '1.5px dashed' : '1px solid'} rgba(${i % 2 === 0 ? '168, 255, 0' : '0, 255, 200'}, ${ring.opacity})`,
            pointerEvents: 'none',
          }}
        />
      ))}

      {/* ── Particle field ── */}
      <AnimatePresence>
        {showParticles && (
          <motion.div
            key="particles"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            style={{
              position: 'absolute',
              width: size * 1.8,
              height: size * 1.8,
              borderRadius: '50%',
              overflow: 'hidden',
              pointerEvents: 'none',
              maskImage: 'radial-gradient(circle at center, black 15%, transparent 65%)',
              WebkitMaskImage: 'radial-gradient(circle at center, black 15%, transparent 65%)',
            }}
          >
            <AuraParticleField density={particleDensity} active={true} mode={particleMode} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── The circular logo core ── */}
      <motion.div
        variants={logoVariants as any}
        animate={state}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          overflow: 'hidden',
          position: 'relative',
          boxShadow: glowStyles[state],
          border: `1.5px solid rgba(168, 255, 0, ${borderOpacity})`,
          background: 'radial-gradient(circle at 50% 50%, rgba(168, 255, 0, 0.06) 0%, rgba(0, 0, 0, 0.95) 60%)',
          transformStyle: 'preserve-3d',
          zIndex: 2,
          willChange: 'transform',
        }}
      >
        <img
          src="/aura-logo.png"
          alt="AURA AI"
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />

        {/* Holographic scan overlay */}
        {(state === 'generating' || state === 'agent') && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              overflow: 'hidden',
              borderRadius: '50%',
              pointerEvents: 'none',
            }}
          >
            <div
              style={{
                position: 'absolute',
                width: '100%',
                height: '3px',
                background: 'linear-gradient(90deg, transparent, rgba(168, 255, 0, 0.5), transparent)',
                animation: 'holo-scan 2s linear infinite',
              }}
            />
          </div>
        )}
      </motion.div>

      {/* ── Orbiting energy dots ── */}
      <AnimatePresence>
        {numDots > 0 && (
          <>
            {Array.from({ length: numDots }).map((_, i) => {
              const dotSpeed = state === 'agent' ? 2.5 : state === 'generating' ? 3 : 5;
              const orbitSize = size * (rings[0]?.scale || 1.3);
              return (
                <motion.div
                  key={`dot-${i}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1, rotate: 360 }}
                  exit={{ opacity: 0 }}
                  transition={{
                    rotate: { duration: dotSpeed, repeat: Infinity, ease: 'linear', delay: i * (dotSpeed / numDots) },
                    opacity: { duration: 0.4 },
                  }}
                  style={{
                    position: 'absolute',
                    width: orbitSize,
                    height: orbitSize,
                    pointerEvents: 'none',
                    zIndex: 3,
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      width: state === 'agent' ? 5 : 4,
                      height: state === 'agent' ? 5 : 4,
                      borderRadius: '50%',
                      background: i % 2 === 0 ? '#A8FF00' : '#00FFC8',
                      boxShadow: `0 0 8px ${i % 2 === 0 ? 'rgba(168, 255, 0, 0.8)' : 'rgba(0, 255, 200, 0.8)'}`,
                    }}
                  />
                </motion.div>
              );
            })}
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

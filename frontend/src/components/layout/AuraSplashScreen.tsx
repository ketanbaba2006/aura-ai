'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AuraParticleField } from '../chat/AuraParticleField';

/**
 * AURA AI Alien-Tech Boot Sequence
 * 8-stage cinematic transformation:
 * 1. Dark void
 * 2. Green particles spiral inward
 * 3. 3 concentric rings materialize
 * 4. Rings rotate independently
 * 5. Logo assembles with 3D flip
 * 6. Circuit energy pulses outward
 * 7. Holographic scan sweeps
 * 8. Flash burst → app
 */
export function AuraSplashScreen({ onComplete }: { onComplete: () => void }) {
  const [stage, setStage] = useState(0);

  const handleComplete = useCallback(() => {
    onComplete();
  }, [onComplete]);

  useEffect(() => {
    const timers = [
      setTimeout(() => setStage(1), 200),   // Particles
      setTimeout(() => setStage(2), 600),   // Rings materialize
      setTimeout(() => setStage(3), 1000),  // Rings spin up
      setTimeout(() => setStage(4), 1200),  // Logo assembles
      setTimeout(() => setStage(5), 1800),  // Circuit pulse
      setTimeout(() => setStage(6), 2200),  // Holo scan
      setTimeout(() => setStage(7), 2600),  // Text + subtitle
      setTimeout(() => handleComplete(), 3200), // Done
    ];
    return () => timers.forEach(clearTimeout);
  }, [handleComplete]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#030303',
        overflow: 'hidden',
      }}
    >
      {/* Stage 1: Particles spiral inward */}
      <AnimatePresence>
        {stage >= 1 && (
          <motion.div
            key="particles"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1 }}
            style={{ position: 'absolute', inset: 0 }}
          >
            <AuraParticleField density={70} mode="spiral" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Central assembly area */}
      <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

        {/* Stage 2-3: Three concentric alien-tech rings */}
        <AnimatePresence>
          {stage >= 2 && (
            <>
              {/* Outer ring — large, dashed, CW */}
              <motion.div
                key="ring-outer"
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: 1,
                  opacity: stage >= 3 ? 0.45 : 0.2,
                  rotate: stage >= 3 ? 360 : 0,
                }}
                transition={{
                  scale: { duration: 0.5, type: 'spring', bounce: 0.3 },
                  opacity: { duration: 0.4 },
                  rotate: { duration: 12, repeat: Infinity, ease: 'linear' },
                }}
                style={{
                  position: 'absolute',
                  width: 220,
                  height: 220,
                  borderRadius: '50%',
                  border: '1.5px dashed rgba(168, 255, 0, 0.6)',
                }}
              />

              {/* Middle ring — solid, CCW */}
              <motion.div
                key="ring-mid"
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: 1,
                  opacity: stage >= 3 ? 0.35 : 0.15,
                  rotate: stage >= 3 ? -360 : 0,
                }}
                transition={{
                  scale: { duration: 0.5, type: 'spring', bounce: 0.3, delay: 0.1 },
                  opacity: { duration: 0.4 },
                  rotate: { duration: 8, repeat: Infinity, ease: 'linear' },
                }}
                style={{
                  position: 'absolute',
                  width: 185,
                  height: 185,
                  borderRadius: '50%',
                  border: '1px solid rgba(0, 255, 200, 0.5)',
                }}
              />

              {/* Inner ring — dotted, CW fast */}
              <motion.div
                key="ring-inner"
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: 1,
                  opacity: stage >= 3 ? 0.3 : 0.1,
                  rotate: stage >= 3 ? 360 : 0,
                }}
                transition={{
                  scale: { duration: 0.5, type: 'spring', bounce: 0.3, delay: 0.2 },
                  opacity: { duration: 0.4 },
                  rotate: { duration: 5, repeat: Infinity, ease: 'linear' },
                }}
                style={{
                  position: 'absolute',
                  width: 155,
                  height: 155,
                  borderRadius: '50%',
                  border: '1px dotted rgba(168, 255, 0, 0.4)',
                }}
              />
            </>
          )}
        </AnimatePresence>

        {/* Stage 5: Circuit pulse — expanding ring flash */}
        <AnimatePresence>
          {stage >= 5 && stage < 7 && (
            <motion.div
              key="circuit-pulse"
              initial={{ scale: 0.5, opacity: 0.8 }}
              animate={{ scale: 3, opacity: 0 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{
                position: 'absolute',
                width: 140,
                height: 140,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(168, 255, 0, 0.4) 0%, rgba(0, 255, 200, 0.1) 40%, transparent 70%)',
              }}
            />
          )}
        </AnimatePresence>

        {/* Stage 4: Logo assembly — blur to sharp with 3D rotateY */}
        <AnimatePresence>
          {stage >= 4 && (
            <motion.div
              key="logo-core"
              initial={{ scale: 0.3, opacity: 0, filter: 'blur(25px)', rotateY: -90 }}
              animate={{
                scale: 1,
                opacity: 1,
                filter: 'blur(0px)',
                rotateY: 0,
                y: stage >= 7 ? [0, -3, 0] : 0,
              }}
              transition={{
                scale: { duration: 0.6, type: 'spring', bounce: 0.35 },
                opacity: { duration: 0.5 },
                filter: { duration: 0.6 },
                rotateY: { duration: 0.8, type: 'spring', bounce: 0.2 },
                y: { duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 0.5 },
              }}
              style={{
                width: 140,
                height: 140,
                borderRadius: '50%',
                overflow: 'hidden',
                position: 'relative',
                boxShadow: '0 0 30px rgba(168, 255, 0, 0.5), 0 0 60px rgba(168, 255, 0, 0.2), 0 0 100px rgba(0, 255, 200, 0.1)',
                border: '2px solid rgba(168, 255, 0, 0.2)',
                background: 'radial-gradient(circle at 50% 50%, rgba(168, 255, 0, 0.08) 0%, rgba(0, 0, 0, 0.95) 55%)',
                zIndex: 5,
              }}
            >
              <img
                src="/aura-logo.png"
                alt="AURA AI"
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              />

              {/* Stage 6: Holographic scan line */}
              {stage >= 6 && (
                <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: '50%', pointerEvents: 'none' }}>
                  <motion.div
                    initial={{ y: '-100%' }}
                    animate={{ y: '200%' }}
                    transition={{ duration: 0.8, ease: 'linear' }}
                    style={{
                      width: '100%',
                      height: '4px',
                      background: 'linear-gradient(90deg, transparent 0%, rgba(168, 255, 0, 0.7) 30%, rgba(0, 255, 200, 0.9) 50%, rgba(168, 255, 0, 0.7) 70%, transparent 100%)',
                      boxShadow: '0 0 15px rgba(168, 255, 0, 0.5), 0 0 30px rgba(0, 255, 200, 0.3)',
                    }}
                  />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stage 7: Title */}
        <AnimatePresence>
          {stage >= 7 && (
            <motion.div
              key="text-block"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 28 }}
            >
              <motion.h1
                initial={{ letterSpacing: '0px' }}
                animate={{ letterSpacing: '10px' }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                className="holo-text"
                style={{
                  fontSize: '22px',
                  fontWeight: '800',
                  textTransform: 'uppercase',
                  fontFamily: 'Inter, sans-serif',
                }}
              >
                AURA AI
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.4 }}
                transition={{ delay: 0.3, duration: 0.5 }}
                style={{
                  marginTop: 8,
                  fontSize: '10px',
                  letterSpacing: '3px',
                  textTransform: 'uppercase',
                  color: 'rgba(168, 255, 0, 0.5)',
                  fontFamily: 'Inter, sans-serif',
                }}
              >
                Autonomous Universal Reasoning Agent
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

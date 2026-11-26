"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AuraLogo } from "../chat/AuraLogo";

interface BootSequenceProps {
  onComplete: () => void;
}

export function BootSequence({ onComplete }: BootSequenceProps) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    // Stage 0: Black screen (0ms)
    // Stage 1: Energy particles (500ms)
    // Stage 2: Quantum rings / AURA logo (1500ms)
    // Stage 3: Neural pathways / Diagnostics (2500ms)
    // Stage 4: OS Online / Reveal (4000ms)

    const timers = [
      setTimeout(() => setStage(1), 500),
      setTimeout(() => setStage(2), 1500),
      setTimeout(() => setStage(3), 2500),
      setTimeout(() => setStage(4), 4000),
      setTimeout(() => {
        onComplete();
      }, 5000), // Fully unmount after 5s
    ];

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  return (
    <AnimatePresence>
      <motion.div
        key="boot-sequence"
        initial={{ opacity: 1 }}
        exit={{ opacity: 0, transition: { duration: 0.8, ease: "easeInOut" } }}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "var(--bg-void)", // Pitch black
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        {/* Stage 1: Energy Particles (Simulated with simple blurred dots) */}
        {stage >= 1 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, ease: "easeOut" }}
            style={{
              position: "absolute",
              width: "100%",
              height: "100%",
              backgroundImage: "radial-gradient(circle at center, rgba(168, 255, 0, 0.05) 0%, transparent 40%)",
              filter: "blur(20px)",
            }}
          />
        )}

        {/* Stage 2 & 3: Logo and Rings */}
        <div style={{ position: "relative", display: "flex", justifyContent: "center", alignItems: "center" }}>
          {stage >= 2 && (
            <>
              {/* Outer Ring */}
              <motion.div
                initial={{ opacity: 0, scale: 0, rotate: -90 }}
                animate={{ opacity: 1, scale: 1, rotate: 360 }}
                transition={{ duration: 3, ease: [0.16, 1, 0.3, 1] }}
                style={{
                  position: "absolute",
                  width: "120px",
                  height: "120px",
                  borderRadius: "50%",
                  border: "1px solid var(--accent-primary)",
                  borderTopColor: "transparent",
                  borderBottomColor: "transparent",
                  opacity: 0.2,
                }}
              />
              
              {/* Core Logo */}
              <motion.div
                initial={{ opacity: 0, scale: 0.5, filter: "blur(10px)" }}
                animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                transition={{ duration: 1, ease: "easeOut" }}
              >
                <AuraLogo size={48} animate={true} />
              </motion.div>
            </>
          )}

          {/* Stage 3: Neural Scans */}
          {stage >= 3 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "140px", opacity: 0.3 }}
              transition={{ duration: 1, ease: "easeInOut" }}
              style={{
                position: "absolute",
                width: "140px",
                borderLeft: "1px solid var(--accent-secondary)",
                borderRight: "1px solid var(--accent-secondary)",
                borderRadius: "50%",
              }}
            />
          )}
        </div>

        {/* Text Diagnostics */}
        <div style={{ height: "40px", marginTop: "32px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <AnimatePresence mode="wait">
            {stage === 2 && (
              <motion.span
                key="stage-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-[10px] tracking-[4px] text-[var(--text-secondary)] uppercase font-medium"
              >
                Initializing Quantum State
              </motion.span>
            )}
            {stage === 3 && (
              <motion.span
                key="stage-3"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-[10px] tracking-[4px] text-[var(--text-secondary)] uppercase font-medium"
              >
                Synchronizing Neural Pathways
              </motion.span>
            )}
            {stage >= 4 && (
              <motion.span
                key="stage-4"
                initial={{ opacity: 0, scale: 0.9, filter: "blur(4px)" }}
                animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="text-[12px] tracking-[6px] text-[var(--text-primary)] uppercase font-bold"
              >
                AURA OS ONLINE
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

/**
 * AURA Floating Card - Premium 3D Mouse Parallax Card
 * Adds depth, dynamic reflection glows, and physical tilt transforms.
 * Optimized with direct DOM manipulation via refs to prevent React state re-renders and lag.
 */

"use client";

import { useRef, HTMLAttributes } from "react";

interface FloatingCardProps extends HTMLAttributes<HTMLDivElement> {
  glowColor?: string;
  maxTilt?: number;
}

export function FloatingCard({
  children,
  style,
  className = "",
  glowColor = "rgba(6, 214, 214, 0.06)",
  maxTilt = 8,
  ...props
}: FloatingCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    const glow = glowRef.current;
    if (!card) return;
    
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Percentage positions from center
    const percentX = (x / rect.width) - 0.5;
    const percentY = (y / rect.height) - 0.5;
    
    // Tilt calculations
    const rotX = -percentY * maxTilt;
    const rotY = percentX * maxTilt;
    
    // Spotlight position
    const glX = (x / rect.width) * 100;
    const glY = (y / rect.height) * 100;
    
    // Apply hardware-accelerated transforms directly to style
    card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.015)`;
    card.style.boxShadow = `0 12px 32px rgba(0,0,0,0.65), 0 0 24px ${glowColor.replace("0.06", "0.15")}`;
    card.style.borderColor = "rgba(255,255,255,0.08)";
    
    if (glow) {
      glow.style.background = `radial-gradient(circle 240px at ${glX}% ${glY}%, ${glowColor}, transparent 80%)`;
      glow.style.opacity = "1";
    }
  };

  const handleMouseEnter = () => {
    const card = cardRef.current;
    const glow = glowRef.current;
    if (card) {
      card.style.transition = "transform 0.05s ease-out, box-shadow 0.3s ease, border-color 0.3s ease";
    }
    if (glow) {
      glow.style.opacity = "1";
    }
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    const glow = glowRef.current;
    if (card) {
      card.style.transition = "transform 0.5s ease, box-shadow 0.3s ease, border-color 0.3s ease";
      card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)";
      card.style.boxShadow = "var(--shadow-sm)";
      card.style.borderColor = "rgba(255,255,255,0.04)";
    }
    if (glow) {
      glow.style.opacity = "0";
    }
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`glass-card ${className}`}
      style={{
        ...style,
        transform: "perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)",
        transition: "transform 0.5s ease, box-shadow 0.3s ease, border-color 0.3s ease",
        position: "relative",
        overflow: "hidden",
        boxShadow: "var(--shadow-sm)",
        borderColor: "rgba(255,255,255,0.04)"
      }}
      {...props}
    >
      {/* Moving Spotlight Reflection Layer */}
      <div
        ref={glowRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `radial-gradient(circle 240px at 50% 50%, ${glowColor}, transparent 80%)`,
          pointerEvents: "none",
          opacity: 0,
          transition: "opacity 0.3s ease",
          zIndex: 0,
        }}
      />
      <div style={{ position: "relative", zIndex: 1, height: "100%", width: "100%" }}>
        {children}
      </div>
    </div>
  );
}

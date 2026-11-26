'use client';

import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  life: number;
  maxLife: number;
  hue: number;
}

interface AuraParticleFieldProps {
  density?: number;
  active?: boolean;
  mode?: 'spiral' | 'rise' | 'orbit';
}

export function AuraParticleField({ density = 25, active = true, mode = 'spiral' }: AuraParticleFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let particles: Particle[] = [];
    let frameCount = 0;

    const resize = () => {
      const parent = canvas.parentElement;
      canvas.width = parent?.clientWidth || 200;
      canvas.height = parent?.clientHeight || 200;
    };

    const resizeObserver = new ResizeObserver(resize);
    if (canvas.parentElement) resizeObserver.observe(canvas.parentElement);
    resize();

    const cx = () => canvas.width / 2;
    const cy = () => canvas.height / 2;
    const maxR = () => Math.min(canvas.width, canvas.height) / 2;

    const createParticle = (): Particle => {
      const angle = Math.random() * Math.PI * 2;

      if (mode === 'spiral') {
        const r = maxR() * (0.6 + Math.random() * 0.4);
        return {
          x: cx() + Math.cos(angle) * r,
          y: cy() + Math.sin(angle) * r,
          vx: 0, vy: 0,
          size: Math.random() * 2 + 0.5,
          alpha: 0, life: 0,
          maxLife: 80 + Math.random() * 80,
          hue: Math.random() > 0.4 ? 80 : 160,
        };
      } else if (mode === 'orbit') {
        const r = maxR() * (0.3 + Math.random() * 0.35);
        return {
          x: cx() + Math.cos(angle) * r,
          y: cy() + Math.sin(angle) * r,
          vx: Math.cos(angle + Math.PI / 2) * (0.3 + Math.random() * 0.5),
          vy: Math.sin(angle + Math.PI / 2) * (0.3 + Math.random() * 0.5),
          size: Math.random() * 1.5 + 0.5,
          alpha: 0, life: 0,
          maxLife: 100 + Math.random() * 100,
          hue: Math.random() > 0.5 ? 80 : 160,
        };
      } else {
        // rise
        return {
          x: Math.random() * canvas.width,
          y: canvas.height + Math.random() * 20,
          vx: (Math.random() - 0.5) * 0.4,
          vy: -0.4 - Math.random() * 1,
          size: Math.random() * 2 + 0.5,
          alpha: 0, life: 0,
          maxLife: 60 + Math.random() * 60,
          hue: Math.random() > 0.5 ? 80 : 160,
        };
      }
    };

    particles = Array.from({ length: density }, createParticle);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      frameCount++;

      if (active && particles.length < density && frameCount % 3 === 0) {
        particles.push(createParticle());
      }

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        if (mode === 'spiral') {
          const dx = cx() - p.x;
          const dy = cy() - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 1) {
            // Spiral inward with tangential velocity
            const nx = dx / dist;
            const ny = dy / dist;
            p.vx = nx * 0.4 + (-ny) * 0.3;
            p.vy = ny * 0.4 + nx * 0.3;
          }
          p.x += p.vx;
          p.y += p.vy;

          const distNow = Math.sqrt((cx() - p.x) ** 2 + (cy() - p.y) ** 2);
          if (distNow < 8) { particles[i] = createParticle(); continue; }
        } else {
          p.x += p.vx;
          p.y += p.vy;
        }

        p.life++;

        // Fade in/out
        const fadeIn = 15;
        const fadeOut = 20;
        if (p.life < fadeIn) {
          p.alpha = (p.life / fadeIn) * 0.7;
        } else if (p.life > p.maxLife - fadeOut) {
          p.alpha = ((p.maxLife - p.life) / fadeOut) * 0.7;
        } else {
          p.alpha = 0.7;
        }

        // Draw glow halo
        if (p.alpha > 0.15) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * 4, 0, Math.PI * 2);
          ctx.fillStyle = `hsla(${p.hue}, 100%, 55%, ${p.alpha * 0.08})`;
          ctx.fill();
        }

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, 100%, 60%, ${Math.max(0, p.alpha)})`;
        ctx.fill();

        if (p.life >= p.maxLife || p.y < -10) {
          particles[i] = createParticle();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      resizeObserver.disconnect();
      cancelAnimationFrame(animationFrameId);
    };
  }, [density, active, mode]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}

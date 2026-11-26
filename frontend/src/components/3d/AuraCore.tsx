'use client';

import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Sparkles, OrbitControls, useTexture, Environment } from '@react-three/drei';
import * as THREE from 'three';

import type { AuraState } from '@/types';

interface AuraCoreProps {
  state?: AuraState;
  className?: string;
}

// ── Quantum Ring Component ──
function CoreRing({ radius, speed, color, thickness = 0.015, rotation, state }: { radius: number; speed: number; color: string; thickness?: number; rotation: [number, number, number], state: AuraState }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const targetSpeed = useMemo(() => {
    switch (state) {
      case 'thinking': return speed * 3;
      case 'researching': return speed * 2;
      case 'planning': return speed * 2.5;
      case 'building': return speed * 4;
      case 'deploying': return speed * 5;
      case 'error': return speed * 0.5;
      case 'generating': return speed * 3;
      default: return speed;
    }
  }, [state, speed]);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * targetSpeed * 0.2;
      meshRef.current.rotation.y += delta * targetSpeed * 0.5;
      meshRef.current.rotation.z += delta * targetSpeed * 0.1;
    }
  });

  return (
    <mesh ref={meshRef} rotation={rotation}>
      <torusGeometry args={[radius, thickness, 32, 100]} />
      <meshPhysicalMaterial 
        color={color}
        emissive={color}
        emissiveIntensity={['thinking', 'planning', 'building', 'deploying', 'generating'].includes(state) ? 2 : 1}
        transparent
        opacity={state === 'idle' ? 0.3 : 0.7}
        wireframe={false}
      />
    </mesh>
  );
}

// ── Holographic Layer (For Agent Mode) ──
function HolographicLayer({ radius, speed }: { radius: number; speed: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * speed;
      meshRef.current.rotation.x += delta * speed * 0.5;
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[radius, 2]} />
      <meshPhysicalMaterial 
        color="#F7F7F8"
        emissive="#F7F7F8"
        emissiveIntensity={0.2}
        transparent
        opacity={0.05}
        wireframe={true}
      />
    </mesh>
  );
}

// ── Central Logo & Core ──
function InnerCore({ state }: { state: AuraState }) {
  const groupRef = useRef<THREE.Group>(null);
  const outerMatRef = useRef<THREE.MeshPhysicalMaterial>(null);
  const timer = useMemo(() => new THREE.Timer(), []);
  const logoTexture = useTexture('/aura-logo.png');
  
  const coreColor = state === 'error' ? '#F87171' : state === 'success' ? '#38BDF8' : '#F7F7F8';
  
  useFrame((_, delta) => {
    timer.update();
    const elapsedTime = timer.getElapsed();

    if (groupRef.current) {
      // Rotation
      groupRef.current.rotation.y += delta * (['researching', 'thinking', 'planning', 'generating'].includes(state) ? 2 : 0.5);
      
      // Pulse Effect
      let scaleBase = 1;
      let scalePulse = 0;
      
      if (['thinking', 'planning', 'generating'].includes(state)) {
        scalePulse = Math.sin(elapsedTime * 4) * 0.05;
      } else if (['building', 'deploying'].includes(state)) {
        scalePulse = Math.sin(elapsedTime * 10) * 0.1;
      } else if (state === 'success') {
        scaleBase = 1.1;
        scalePulse = Math.sin(elapsedTime * 6) * 0.08;
      } else if (state === 'error') {
        // Sharp, controlled red pulse
        scalePulse = Math.sin(elapsedTime * 8) * 0.03;
      } else {
        // Soft green energy pulse (idle)
        scalePulse = Math.sin(elapsedTime * 2) * 0.02;
      }
      
      groupRef.current.scale.setScalar(scaleBase + scalePulse);
    }
    
    if (outerMatRef.current) {
      outerMatRef.current.emissiveIntensity = state === 'success' ? 2 : state === 'error' ? 2 : 1;
    }
  });

  return (
    <group ref={groupRef}>
      <mesh>
        <sphereGeometry args={[0.9, 64, 64]} />
        <meshPhysicalMaterial 
          ref={outerMatRef}
          color={coreColor} 
          emissive={coreColor} 
          emissiveIntensity={0.2} 
          transmission={0.9} /* Glass effect */
          opacity={1}
          metalness={0}
          roughness={0.1}
          ior={1.5}
          thickness={0.5}
          transparent
        />
      </mesh>
      <sprite scale={[0.7, 0.7, 0.7]}>
        <spriteMaterial map={logoTexture} transparent opacity={1} />
      </sprite>
    </group>
  );
}

export function AuraCore({ state = 'idle', className = "w-full h-full min-h-[200px]" }: AuraCoreProps) {
  const getAccentColor = () => {
    if (state === 'error') return '#F87171';
    if (state === 'success') return '#38BDF8';
    return '#E5E5E5';
  };

  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0, 4.5], fov: 45 }}>
        <ambientLight intensity={1.5} />
        <directionalLight position={[10, 10, 5]} intensity={2} color="#ffffff" />
        <directionalLight position={[-10, -10, -5]} intensity={1} color="#A8FF00" />
        <React.Suspense fallback={null}>
        <Environment preset="city" />
        
        <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
          <group>
            {/* Inner Core */}
            <InnerCore state={state} />
            
            {/* Orbiting Quantum Rings (Thinking, Research, Agent, Success, Error) */}
            {state !== 'idle' && (
              <>
                <CoreRing radius={1.3} speed={1.2} color={getAccentColor()} rotation={[Math.PI/4, 0, 0]} state={state} />
                <CoreRing radius={1.7} speed={-0.8} color={state === 'error' ? '#F87171' : '#38BDF8'} rotation={[0, Math.PI/3, 0]} state={state} />
              </>
            )}

            {/* Holographic Layers for Active Builder/Deploy Modes */}
            {['building', 'deploying', 'planning'].includes(state) && (
              <>
                <HolographicLayer radius={2.2} speed={0.5} />
                <HolographicLayer radius={2.5} speed={-0.3} />
                <CoreRing radius={2.8} speed={2} color="#F7F7F8" rotation={[Math.PI/2, Math.PI/4, 0]} state={state} thickness={0.01} />
              </>
            )}
            
            {/* Data Particles for Research / Thinking */}
            {['researching', 'thinking', 'planning', 'generating'].includes(state) && (
              <Sparkles 
                count={state === 'researching' ? 300 : 100} 
                scale={3.5} 
                size={1.5} 
                speed={state === 'researching' ? 3 : 1} 
                color={getAccentColor()} 
              />
            )}
          </group>
        </Float>
        </React.Suspense>
        
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={state === 'idle'} autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}

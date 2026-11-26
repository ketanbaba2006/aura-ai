'use client';

import React, { useState } from 'react';
import { BootSequence } from './BootSequence';

export function AppWrapper({ children }: { children: React.ReactNode }) {
  const [booted, setBooted] = useState(false);

  return (
    <>
      {!booted && <BootSequence onComplete={() => setBooted(true)} />}
      <div 
        className="app-shell"
        style={{ 
          opacity: booted ? 1 : 0, 
          transition: 'opacity 1s ease-in-out',
          pointerEvents: booted ? 'auto' : 'none'
        }}
      >
        {children}
      </div>
    </>
  );
}

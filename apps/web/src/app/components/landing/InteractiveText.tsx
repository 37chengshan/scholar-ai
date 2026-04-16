import React, { useRef, useEffect } from 'react';

export const physicsNodes: {
  el: HTMLElement;
  x: number;
  y: number;
  vx: number;
  vy: number;
}[] = [];

export function InteractiveText({ text, className }: { text: string; className?: string }) {
  const containerRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    const spans = Array.from(containerRef.current.children) as HTMLElement[];
    
    const nodes = spans.map(span => ({
      el: span,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
    }));
    
    physicsNodes.push(...nodes);
    
    return () => {
      nodes.forEach(n => {
        const idx = physicsNodes.indexOf(n);
        if (idx !== -1) physicsNodes.splice(idx, 1);
      });
    };
  }, [text]);

  return (
    <span ref={containerRef} className={className} style={{ display: 'inline' }}>
      {text.split('').map((char, i) => (
        <span 
          key={i} 
          style={{ display: 'inline-block', transition: 'none', transformOrigin: 'center' }}
        >
          {char === ' ' ? '\u00A0' : char}
        </span>
      ))}
    </span>
  );
}
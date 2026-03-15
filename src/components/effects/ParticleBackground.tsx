import React, { useEffect, useRef, useCallback } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  originalX: number;
  originalY: number;
}

interface MousePosition {
  x: number;
  y: number;
}

export const ParticleBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>();
  const mouseRef = useRef<MousePosition>({ x: -1000, y: -1000 });
  const isActiveRef = useRef(true);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    mouseRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = { x: -1000, y: -1000 };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Reset active state on mount
    isActiveRef.current = true;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Initialize particles with higher density on right side
    const baseCount = 60;
    const rightSideExtraCount = 40;
    particlesRef.current = [];

    // Base particles spread across screen
    for (let i = 0; i < baseCount; i++) {
      const x = Math.random() * canvas.width;
      const y = Math.random() * canvas.height;
      particlesRef.current.push({
        x,
        y,
        originalX: x,
        originalY: y,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    // Extra particles concentrated on right side (60% to 100% of width)
    for (let i = 0; i < rightSideExtraCount; i++) {
      const x = canvas.width * (0.6 + Math.random() * 0.4);
      const y = Math.random() * canvas.height;
      particlesRef.current.push({
        x,
        y,
        originalX: x,
        originalY: y,
        vx: (Math.random() - 0.5) * 0.5 + 0.1, // Slight rightward bias
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2.5 + 1,
        opacity: Math.random() * 0.6 + 0.3,
      });
    }

    const animate = () => {
      if (!isActiveRef.current) {
        // Restart animation if it was stopped but component is still mounted
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const particles = particlesRef.current;
      const mouse = mouseRef.current;

      // Update and draw particles
      particles.forEach((particle, i) => {
        // Mouse interaction - particles are attracted to mouse
        const dx = mouse.x - particle.x;
        const dy = mouse.y - particle.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = 200;

        if (distance < maxDistance && distance > 0) {
          const force = (maxDistance - distance) / maxDistance;
          const angle = Math.atan2(dy, dx);
          particle.vx += Math.cos(angle) * force * 0.5;
          particle.vy += Math.sin(angle) * force * 0.5;
        }

        // Apply friction
        particle.vx *= 0.98;
        particle.vy *= 0.98;

        // Add base movement
        particle.x += particle.vx + (Math.random() - 0.5) * 0.1;
        particle.y += particle.vy + (Math.random() - 0.5) * 0.1;

        // Return to original position slowly
        const returnX = (particle.originalX - particle.x) * 0.01;
        const returnY = (particle.originalY - particle.y) * 0.01;
        particle.x += returnX;
        particle.y += returnY;

        // Wrap around edges
        if (particle.x < 0) {
          particle.x = canvas.width;
          particle.originalX = canvas.width;
        }
        if (particle.x > canvas.width) {
          particle.x = 0;
          particle.originalX = 0;
        }
        if (particle.y < 0) {
          particle.y = canvas.height;
          particle.originalY = canvas.height;
        }
        if (particle.y > canvas.height) {
          particle.y = 0;
          particle.originalY = 0;
        }

        // Update original position for flowing effect
        particle.originalX += particle.vx * 0.1;
        particle.originalY += particle.vy * 0.1;

        // Draw particle
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 245, 255, ${particle.opacity})`;
        ctx.fill();

        // Draw glow
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size * 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 245, 255, ${particle.opacity * 0.3})`;
        ctx.fill();

        // Draw connections
        particles.slice(i + 1).forEach((other) => {
          const dx = particle.x - other.x;
          const dy = particle.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(other.x, other.y);
            ctx.strokeStyle = `rgba(0, 245, 255, ${0.15 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      // Draw mouse glow
      if (mouse.x > 0) {
        const gradient = ctx.createRadialGradient(
          mouse.x, mouse.y, 0,
          mouse.x, mouse.y, 150
        );
        gradient.addColorStop(0, 'rgba(0, 245, 255, 0.1)');
        gradient.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, 150, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    // Visibility change handler
    const handleVisibilityChange = () => {
      isActiveRef.current = document.visibilityState === 'visible';
      if (isActiveRef.current) {
        animate();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      isActiveRef.current = false;
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [handleMouseMove, handleMouseLeave]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{
        zIndex: 0,
        background: 'transparent',
      }}
    />
  );
};

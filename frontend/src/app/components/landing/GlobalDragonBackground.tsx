import React, { useEffect, useRef } from 'react';
import { physicsNodes } from './InteractiveText';

export function GlobalDragonBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    // State
    let mouseX = width / 2;
    let mouseY = height / 2;
    let isMouseDown = false;

    // Dragon Setup
    const numSegments = 50;
    const segments: any[] = Array(numSegments).fill(0).map(() => ({ x: width/2, y: height/2, angle: 0 }));
    const segLength = 12;

    const particles: any[] = [];

    // Animation Loop
    let animationFrameId: number;

    function render() {
      if (!ctx) return;
      // Clear background with a paper-like color
      ctx.fillStyle = '#f4eee0';
      ctx.fillRect(0, 0, width, height);

      // 1.5 Update DOM Top-Level Text Physics
      physicsNodes.forEach(node => {
        if (!node.el.offsetParent) return; // skip hidden nodes

        const rect = node.el.getBoundingClientRect();
        // Calculate the absolute center of the node's base layout position
        const cx = rect.left + rect.width / 2 - node.x;
        const cy = rect.top + rect.height / 2 - node.y;

        // Spring to original layout position (0,0 relative)
        node.vx += (0 - node.x) * 0.1;
        node.vy += (0 - node.y) * 0.1;

        // Repel from Dragon body (sample every 3rd segment)
        for (let i = 0; i < segments.length; i += 3) {
          const seg = segments[i];
          const dx = cx + node.x - seg.x;
          const dy = cy + node.y - seg.y;
          const distSq = dx * dx + dy * dy;
          const radius = 120; // Larger repulsion radius for UI text
          if (distSq < radius * radius) {
            const dist = Math.sqrt(distSq) || 1;
            const force = Math.pow((radius - dist) / radius, 2) * 12;
            node.vx += (dx / dist) * force;
            node.vy += (dy / dist) * force;
          }
        }

        // Repel from Mouse/Head directly
        const dxM = cx + node.x - mouseX;
        const dyM = cy + node.y - mouseY;
        const distSqM = dxM * dxM + dyM * dyM;
        if (distSqM < 160 * 160) {
            const distM = Math.sqrt(distSqM) || 1;
            const forceM = Math.pow((160 - distM) / 160, 2) * 20;
            node.vx += (dxM / distM) * forceM;
            node.vy += (dyM / distM) * forceM;
        }

        // Also shake if fire breathing
        if (isMouseDown && distSqM < 300 * 300) {
          node.vx += (Math.random() - 0.5) * 6;
          node.vy += (Math.random() - 0.5) * 6;
        }

        // Dampen and apply
        node.vx *= 0.75;
        node.vy *= 0.75;
        node.x += node.vx;
        node.y += node.vy;

        // Apply transform. Only update if moving to save layout thrashing
        if (Math.abs(node.x) > 0.5 || Math.abs(node.y) > 0.5 || Math.abs(node.vx) > 0.1 || Math.abs(node.vy) > 0.1) {
          node.el.style.transform = `translate3d(${node.x}px, ${node.y}px, 0)`;
        } else {
          node.el.style.transform = 'none';
          node.x = 0;
          node.y = 0;
          node.vx = 0;
          node.vy = 0;
        }
      });

      // 2. Update Dragon IK
      const head = segments[0];
      const dx = mouseX - head.x;
      const dy = mouseY - head.y;

      // Move head smoothly towards mouse
      head.x += dx * 0.2;
      head.y += dy * 0.2;
      head.angle = Math.atan2(dy, dx);

      // Resolve IK chain
      for (let i = 1; i < segments.length; i++) {
        const prev = segments[i - 1];
        const curr = segments[i];
        const angle = Math.atan2(prev.y - curr.y, prev.x - curr.x);
        curr.x = prev.x - Math.cos(angle) * segLength;
        curr.y = prev.y - Math.sin(angle) * segLength;
        curr.angle = angle;
      }

      // 3. Draw Winged Dragon
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Helper function for body radius
      const getRadius = (i: number) => {
        if (i < 12) return 10 + (i/12) * 12; // Head to chest: 10 to 22
        return 22 * Math.pow(1 - (i-12)/(segments.length-12), 1.2); // Chest to tail: 22 to 0
      };

      // Draw Wings (attached around segment 12)
      const wingBase = segments[12];
      if (wingBase && segments[22]) {
        const flap = Math.sin(Date.now() * 0.005) * 0.6; // Flap angle

        const drawWing = (sideMult: number) => {
          const baseAngle = wingBase.angle + (Math.PI/2 - 0.4) * sideMult;
          const armLength = 70;

          // Joint (elbow)
          const jointX = wingBase.x + Math.cos(baseAngle + flap * sideMult) * armLength;
          const jointY = wingBase.y + Math.sin(baseAngle + flap * sideMult) * armLength;

          // Fingers spread from joint
          const fingerAngles = [-0.1, 0.4, 0.9];
          const fingerLengths = [140, 130, 110];
          const tips = [];

          for (let i = 0; i < 3; i++) {
            const fAngle = baseAngle + flap * sideMult + fingerAngles[i] * sideMult;
            tips.push({
              x: jointX + Math.cos(fAngle) * fingerLengths[i],
              y: jointY + Math.sin(fAngle) * fingerLengths[i]
            });
          }

          // Membrane
          ctx.beginPath();
          ctx.moveTo(wingBase.x, wingBase.y);
          ctx.lineTo(jointX, jointY);
          ctx.lineTo(tips[0].x, tips[0].y);

          // Curves between tips
          ctx.quadraticCurveTo(
            (tips[0].x + tips[1].x)/2 - Math.cos(baseAngle)*25,
            (tips[0].y + tips[1].y)/2 - Math.sin(baseAngle)*25,
            tips[1].x, tips[1].y
          );
          ctx.quadraticCurveTo(
            (tips[1].x + tips[2].x)/2 - Math.cos(baseAngle)*25,
            (tips[1].y + tips[2].y)/2 - Math.sin(baseAngle)*25,
            tips[2].x, tips[2].y
          );

          // Connect back to body
          const bodyAttach = segments[22];
          ctx.quadraticCurveTo(
            wingBase.x + Math.cos(baseAngle)*40,
            wingBase.y + Math.sin(baseAngle)*40,
            bodyAttach.x, bodyAttach.y
          );

          ctx.fillStyle = 'rgba(18, 18, 18, 0.95)'; // Sleek dark membrane
          ctx.fill();

          // Bone structure
          ctx.beginPath();
          ctx.moveTo(wingBase.x, wingBase.y);
          ctx.lineTo(jointX, jointY);
          ctx.lineTo(tips[0].x, tips[0].y);
          ctx.moveTo(jointX, jointY);
          ctx.lineTo(tips[1].x, tips[1].y);
          ctx.moveTo(jointX, jointY);
          ctx.lineTo(tips[2].x, tips[2].y);
          ctx.strokeStyle = '#2a2a2a';
          ctx.lineWidth = 3;
          ctx.stroke();
        };

        drawWing(-1); // Left
        drawWing(1);  // Right
      }

      // Draw Smooth Body
      ctx.beginPath();
      // Left side outline
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const r = getRadius(i);
        const px = seg.x + Math.cos(seg.angle + Math.PI/2) * r;
        const py = seg.y + Math.sin(seg.angle + Math.PI/2) * r;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      // Right side outline (reversed)
      for (let i = segments.length - 1; i >= 0; i--) {
        const seg = segments[i];
        const r = getRadius(i);
        ctx.lineTo(seg.x + Math.cos(seg.angle - Math.PI/2) * r, seg.y + Math.sin(seg.angle - Math.PI/2) * r);
      }
      ctx.fillStyle = '#111111';
      ctx.fill();

      // Body Spikes / Scales
      ctx.strokeStyle = '#2a2a2a';
      ctx.lineWidth = 2;
      for (let i = 4; i < segments.length - 5; i += 4) {
        const seg = segments[i];
        const r = getRadius(i);

        ctx.beginPath();
        ctx.moveTo(seg.x + Math.cos(seg.angle + Math.PI/2) * r, seg.y + Math.sin(seg.angle + Math.PI/2) * r);
        ctx.lineTo(seg.x + Math.cos(seg.angle + Math.PI/2) * (r + 8), seg.y + Math.sin(seg.angle + Math.PI/2) * (r + 8));
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(seg.x + Math.cos(seg.angle - Math.PI/2) * r, seg.y + Math.sin(seg.angle - Math.PI/2) * r);
        ctx.lineTo(seg.x + Math.cos(seg.angle - Math.PI/2) * (r + 8), seg.y + Math.sin(seg.angle - Math.PI/2) * (r + 8));
        ctx.stroke();
      }

      // Tail Spade
      const tail = segments[segments.length - 1];
      ctx.save();
      ctx.translate(tail.x, tail.y);
      ctx.rotate(tail.angle);
      ctx.fillStyle = '#111111';
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(-12, -10);
      ctx.lineTo(-28, 0);
      ctx.lineTo(-12, 10);
      ctx.closePath();
      ctx.fill();
      ctx.restore();

      // Draw Head (Sleek Western Dragon)
      ctx.save();
      ctx.translate(head.x, head.y);
      ctx.rotate(head.angle);
      ctx.fillStyle = '#111111';

      // Main skull
      ctx.beginPath();
      ctx.moveTo(32, 0);    // Snout
      ctx.lineTo(12, -8);
      ctx.lineTo(-5, -14);  // Brow
      ctx.lineTo(-18, -6);  // Back
      ctx.lineTo(-18, 6);
      ctx.lineTo(-5, 14);
      ctx.lineTo(12, 8);
      ctx.closePath();
      ctx.fill();

      // Swept-back Horns
      ctx.beginPath();
      ctx.moveTo(-5, -12);
      ctx.quadraticCurveTo(-20, -18, -35, -30);
      ctx.lineTo(-22, -8);
      ctx.closePath();
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(-5, 12);
      ctx.quadraticCurveTo(-20, 18, -35, 30);
      ctx.lineTo(-22, 8);
      ctx.closePath();
      ctx.fill();

      // Glowing fierce eyes
      ctx.fillStyle = '#ff3300';
      ctx.beginPath();
      ctx.ellipse(8, -6, 4, 1.5, Math.PI/6, 0, Math.PI*2);
      ctx.ellipse(8, 6, 4, 1.5, -Math.PI/6, 0, Math.PI*2);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(9, -6, 1, 0, Math.PI*2);
      ctx.arc(9, 6, 1, 0, Math.PI*2);
      ctx.fill();

      ctx.restore();

      // 4. Update and Draw Fire Particles
      if (isMouseDown) {
        // Spawn fire
        for(let i=0; i<5; i++) {
          particles.push({
            x: head.x + Math.cos(head.angle) * 35,
            y: head.y + Math.sin(head.angle) * 35,
            vx: Math.cos(head.angle) * (18 + Math.random()*8) + (Math.random()-0.5)*10,
            vy: Math.sin(head.angle) * (18 + Math.random()*8) + (Math.random()-0.5)*10,
            life: 1.0,
            color: ['#ff1a00', '#ff5500', '#ff9900', '#ffffff', '#ffcc00'][Math.floor(Math.random()*5)]
          });
        }
      }

      ctx.globalCompositeOperation = 'screen';
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vx *= 0.92;
        p.vy *= 0.92;
        p.life -= 0.015;

        if (p.life <= 0) {
          particles.splice(i, 1);
        } else {
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.life;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.life * 12 + 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1.0;
      ctx.globalCompositeOperation = 'source-over';

      animationFrameId = requestAnimationFrame(render);
    }

    render();

    // Event Listeners
    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    const handleMouseDown = () => isMouseDown = true;
    const handleMouseUp = () => isMouseDown = false;
    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="fixed inset-0 w-full h-full z-0 overflow-hidden pointer-events-none">
      <canvas
        ref={canvasRef}
        className="block w-full h-full"
        style={{ touchAction: 'none' }}
      />
    </div>
  );
}
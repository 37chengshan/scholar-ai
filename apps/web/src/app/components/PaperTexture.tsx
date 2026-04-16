interface PaperTextureProps {
  opacity?: number;
}

export function PaperTexture({ opacity = 0.05 }: PaperTextureProps) {
  return (
    <svg
      className="fixed inset-0 w-full h-full pointer-events-none z-50 mix-blend-multiply"
      style={{ opacity }}
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
    >
      <filter id="noiseFilter">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#noiseFilter)" />
    </svg>
  );
}

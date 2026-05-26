export default function GrainOverlay() {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-[999] h-full w-full"
      style={{ opacity: 0.032 }}
    >
      <filter id="grain">
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.65"
          numOctaves="3"
          stitchTiles="stitch"
        />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  );
}

interface GlowEffectProps {
  className?: string;
  size?: number;
  color?: string;
}

export default function GlowEffect({
  className = "",
  size = 400,
  color = "rgba(235,110,18,0.18)",
}: GlowEffectProps) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute rounded-full ${className}`}
      style={{
        width: size,
        height: size,
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        filter: "blur(60px)",
        animation: "glowPulse 4s ease-in-out infinite",
      }}
    />
  );
}

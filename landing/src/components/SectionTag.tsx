interface SectionTagProps {
  children: React.ReactNode;
}

export default function SectionTag({ children }: SectionTagProps) {
  return (
    <span
      className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--text-muted)] border border-[var(--border)] px-3 py-1 rounded-sm"
      style={{ letterSpacing: "0.18em" }}
    >
      <span
        className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)]"
        aria-hidden="true"
      />
      {children}
    </span>
  );
}

import { motion } from "framer-motion";

interface MetricCardProps {
  value: string;
  label: string;
  sub: string;
  delay?: number;
}

export default function MetricCard({ value, label, sub, delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      className="border border-[var(--border)] bg-[var(--surface)] p-6 rounded-sm flex flex-col gap-2 group hover:border-[var(--border-hi)] transition-colors duration-300 relative overflow-hidden"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.56, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="absolute inset-0 bg-[var(--accent-glow)] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
      <span className="font-mono text-3xl font-bold text-[var(--text)] tabular-nums tracking-tight">
        {value}
      </span>
      <span className="font-mono text-[13px] text-[var(--text-muted)] leading-snug">{label}</span>
      <span className="font-mono text-[11px] text-[var(--accent)] uppercase tracking-widest mt-auto">
        {sub}
      </span>
    </motion.div>
  );
}

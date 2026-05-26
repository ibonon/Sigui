import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import MetricCard from "./MetricCard";
import { metrics } from "../data";

export default function MetricsSection() {
  return (
    <Section id="metrics" className="py-48 md:py-64 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8 mb-16">
          <div>
            <SectionTag>Receipts.</SectionTag>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.1 }}
              className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight"
            >
              Les chiffres<br />
              <span className="font-italic italic text-[var(--accent)]">parlent d'eux-mêmes.</span>
            </motion.h2>
          </div>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.2 }}
            className="font-mono text-[13px] text-[var(--text-muted)] leading-relaxed max-w-sm"
          >
            Imina-Na V2, entraîné et validé sur des données réelles de menaces IA.
            Open-source, auditable, reproductible.
          </motion.p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-px bg-[var(--border)]">
          {metrics.map((m, i) => (
            <MetricCard
              key={m.label}
              value={m.value}
              label={m.label}
              sub={m.sub}
              delay={i * 0.07}
            />
          ))}
        </div>
      </div>
    </Section>
  );
}

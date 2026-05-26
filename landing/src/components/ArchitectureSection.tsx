import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import GlowEffect from "./GlowEffect";
import { architectureSteps } from "../data";

export default function ArchitectureSection() {
  return (
    <Section id="architecture" className="py-32 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="flex flex-col items-center text-center mb-16">
          <SectionTag>Architecture</SectionTag>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight max-w-2xl"
          >
            5 couches de risque.<br />
            <span className="font-italic italic text-[var(--accent)]">Zéro compromis.</span>
          </motion.h2>
        </div>

        {/* Pipeline visualization */}
        <div className="relative">
          <GlowEffect className="top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" size={600} />

          {/* Desktop: horizontal */}
          <div className="hidden md:flex items-center justify-between relative">
            {/* Connecting line */}
            <div className="absolute top-1/2 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/40 to-transparent -translate-y-1/2 z-0" />

            {architectureSteps.map((step, i) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 32 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.56, delay: i * 0.12 }}
                className="relative z-10 flex flex-col items-center gap-3 flex-1"
              >
                {/* Node */}
                <div
                  className="w-16 h-16 border-2 border-[var(--border)] bg-[var(--surface)] rounded-sm flex items-center justify-center text-2xl relative group hover:border-[var(--accent)]/60 transition-colors duration-300"
                >
                  <div className="absolute inset-0 bg-[var(--accent-glow)] opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-sm" />
                  <span className="relative z-10">{step.icon}</span>
                </div>
                {/* Arrow (between nodes) */}
                {i < architectureSteps.length - 1 && (
                  <div className="absolute top-8 -right-3 text-[var(--accent)] font-mono text-lg z-20 hidden lg:block">→</div>
                )}
                <div className="text-center">
                  <div className="font-mono text-[12px] font-medium text-[var(--text)] mb-1">{step.label}</div>
                  <div className="font-mono text-[11px] text-[var(--text-muted)] max-w-[120px] leading-snug">{step.desc}</div>
                </div>
                {/* Step number */}
                <div className="font-mono text-[10px] text-[var(--accent)] uppercase tracking-widest">0{step.id}</div>
              </motion.div>
            ))}
          </div>

          {/* Mobile: vertical */}
          <div className="md:hidden flex flex-col gap-4">
            {architectureSteps.map((step, i) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -24 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.56, delay: i * 0.1 }}
                className="flex items-center gap-4 border border-[var(--border)] bg-[var(--surface)] p-4 rounded-sm"
              >
                <div className="w-12 h-12 flex items-center justify-center text-xl flex-shrink-0 border border-[var(--border)] rounded-sm bg-[var(--bg)]">
                  {step.icon}
                </div>
                <div>
                  <div className="font-mono text-[12px] font-medium text-[var(--text)]">
                    <span className="text-[var(--accent)] mr-2">0{step.id}</span>{step.label}
                  </div>
                  <div className="font-mono text-[11px] text-[var(--text-muted)] mt-0.5">{step.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Bottom note */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-16 text-center border border-[var(--border)] bg-[var(--surface)] rounded-sm p-6"
        >
          <p className="font-mono text-[12px] text-[var(--text-muted)] leading-relaxed">
            Chaque couche s'exécute en <span className="text-[var(--text)]">parallèle</span> pour maintenir une latence globale &lt;50ms.
            Le verdict final déclenche la génération d'une <span className="text-[var(--text)]">preuve ZK-STARK</span> ancrée on-chain,
            indépendamment du résultat.
          </p>
        </motion.div>
      </div>
    </Section>
  );
}

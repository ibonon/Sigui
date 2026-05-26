import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import { features } from "../data";

export default function FeaturesSection() {
  return (
    <Section id="features" className="py-32 px-6">
      <div className="container mx-auto max-w-[1160px]">
        <div className="flex flex-col items-center text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <SectionTag>Fonctionnalités</SectionTag>
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight max-w-2xl"
          >
            La sécurité comme<br />
            <span className="font-italic italic text-[var(--accent)]">infrastructure native.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.18 }}
            className="font-mono text-[13px] text-[var(--text-muted)] mt-5 max-w-xl leading-relaxed"
          >
            Chaque couche du pipeline Sigui est conçue pour les contraintes réelles des agents autonomes —
            vitesse, décentralisation, vérifiabilité.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-[var(--border)]">
          {features.map((f, i) => (
            <motion.div
              key={f.id}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.56, delay: i * 0.08 }}
              className="bg-[var(--bg)] p-8 group hover:bg-[var(--surface)] transition-colors duration-300 relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-[var(--accent-glow)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              <div className="flex items-start gap-4 relative">
                <span className="text-2xl">{f.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="font-mono text-[13px] font-medium text-[var(--text)]">{f.title}</h3>
                  </div>
                  <p className="font-mono text-[12px] text-[var(--text-muted)] leading-relaxed mb-4">
                    {f.description}
                  </p>
                  <span className="inline-block font-mono text-[10px] uppercase tracking-widest text-[var(--accent)] border border-[var(--accent)]/30 px-2 py-0.5 rounded-sm">
                    {f.badge}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

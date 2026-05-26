import React from "react";
import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import GlowEffect from "./GlowEffect";

export default function TrustformerSection() {
  return (
    <Section id="trustformer" className="py-32 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left — text */}
          <div>
            <SectionTag>Recherche</SectionTag>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.1 }}
              className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 mb-5 tracking-tight"
            >
              Trustformer.<br />
              <span className="font-italic italic text-[var(--accent)]">La prochaine génération.</span>
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.18 }}
              className="font-mono text-[13px] text-[var(--text-muted)] leading-relaxed mb-6"
            >
              Une architecture native qui élimine entièrement le rendu PNG intermédiaire.
              Attention pondérée par la réputation on-chain, latence cible{" "}
              <span className="text-[var(--text)]">&lt;5ms</span>. Trustformer repense
              l'inspection visuelle comme un problème de langage structuré.
            </motion.p>

            {/* Feature bullets */}
            <motion.ul
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.25 }}
              className="space-y-3 mb-8"
            >
              {[
                { icon: "⚡", text: "Latence cible <5ms (vs 50ms actuel)" },
                { icon: "🔗", text: "Attention pondérée par réputation on-chain (ERC-8259)" },
                { icon: "🖼️", text: "Élimination du rendu PNG — traitement natif du DOM" },
                { icon: "🧠", text: "Architecture Transformer fine-tunée sur menaces IA" },
              ].map((item) => (
                <li key={item.text} className="flex items-start gap-3">
                  <span className="mt-0.5">{item.icon}</span>
                  <span className="font-mono text-[12px] text-[var(--text-muted)]">{item.text}</span>
                </li>
              ))}
            </motion.ul>

            <motion.a
              href="#"
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.3 }}
              whileHover={{ x: 4 }}
              className="inline-flex items-center gap-2 font-mono text-[13px] text-[var(--accent)] hover:underline underline-offset-4"
            >
              Lire le preprint arXiv →
            </motion.a>
          </div>

          {/* Right — visual card */}
          <div className="relative">
            <GlowEffect className="-top-20 -right-20" size={350} />
            <motion.div
              initial={{ opacity: 0, x: 32 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.15 }}
              className="border border-[var(--border)] bg-[var(--surface)] rounded-sm overflow-hidden"
            >
              <div className="border-b border-[var(--border)] bg-[var(--surface-2)] px-5 py-3 flex items-center justify-between">
                <span className="font-mono text-[11px] text-[var(--text-muted)]">trustformer — architecture</span>
                <span className="font-mono text-[10px] text-[var(--accent)] uppercase tracking-widest">Preprint</span>
              </div>
              <div className="p-6 space-y-4">
                {/* Comparison table */}
                <div className="grid grid-cols-3 gap-px bg-[var(--border)] rounded-sm overflow-hidden text-center">
                  <div className="bg-[var(--bg)] p-3">
                    <div className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-widest mb-2">Métrique</div>
                  </div>
                  <div className="bg-[var(--bg)] p-3">
                    <div className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-widest mb-2">Imina-Na V2</div>
                  </div>
                  <div className="bg-[var(--bg)] p-3 border-l-2 border-[var(--accent)]/40">
                    <div className="font-mono text-[10px] text-[var(--accent)] uppercase tracking-widest mb-2">Trustformer</div>
                  </div>
                  {[
                    ["Latence", "38ms", "<5ms"],
                    ["F1-Score", "92.9%", "~97%*"],
                    ["Rendu PNG", "Requis", "Natif"],
                    ["On-Chain", "Post-verdict", "Pondération"],
                  ].map(([metric, v1, v2]) => (
                    <React.Fragment key={metric}>
                      <div className="bg-[var(--bg)] p-3 border-t border-[var(--border)]">
                        <span className="font-mono text-[11px] text-[var(--text-muted)]">{metric}</span>
                      </div>
                      <div className="bg-[var(--bg)] p-3 border-t border-[var(--border)]">
                        <span className="font-mono text-[11px] text-[var(--text)]">{v1}</span>
                      </div>
                      <div className="bg-[var(--bg)] p-3 border-t border-[var(--border)] border-l-2 border-l-[var(--accent)]/40">
                        <span className="font-mono text-[11px] text-[var(--accent)] font-medium">{v2}</span>
                      </div>
                    </React.Fragment>
                  ))}
                </div>
                <p className="font-mono text-[10px] text-[var(--text-muted)]">* Estimations préliminaires. Preprint en cours de soumission.</p>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </Section>
  );
}

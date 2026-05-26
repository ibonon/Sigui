import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import CodeBlock from "./CodeBlock";
import GlowEffect from "./GlowEffect";
import { codeExample } from "../data";

export default function InstallSection() {
  return (
    <Section id="install" className="py-48 md:py-64 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div>
            <SectionTag>Installation</SectionTag>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.1 }}
              className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 mb-5 tracking-tight"
            >
              Une ligne.<br />
              <span className="font-italic italic text-[var(--accent)]">Sécurité réelle.</span>
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.18 }}
              className="font-mono text-[13px] text-[var(--text-muted)] leading-relaxed mb-8"
            >
              Un décorateur Python suffit pour sécuriser votre agent. Sigui intercepte,
              inspecte et rend son verdict avant toute exécution, sans modifier votre logique métier.
            </motion.p>

            {/* Badges */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.25 }}
              className="flex flex-wrap gap-2"
            >
              {[
                { label: "PyPI", href: "https://pypi.org/project/sigui-sdk/", badge: "v0.1.0" },
                { label: "License", href: "#", badge: "MIT" },
                { label: "Python", href: "#", badge: "3.10+" },
              ].map((b) => (
                <a
                  key={b.label}
                  href={b.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center font-mono text-[11px] border border-[var(--border)] rounded-sm overflow-hidden hover:border-[var(--border-hi)] transition-colors duration-200"
                >
                  <span className="px-2.5 py-1 bg-[var(--surface-2)] text-[var(--text-muted)]">{b.label}</span>
                  <span className="px-2.5 py-1 bg-[var(--accent)] text-[var(--bg)] font-medium">{b.badge}</span>
                </a>
              ))}
            </motion.div>
          </div>

          {/* Right — terminal blocks */}
          <div className="flex flex-col gap-4 relative">
            <GlowEffect className="-top-20 -right-20" size={300} />

            {/* Install command */}
            <motion.div
              initial={{ opacity: 0, x: 24 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              <div className="border border-[var(--border)] bg-[var(--surface)] rounded-sm overflow-hidden">
                <div className="border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-2 flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                    <span className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                    <span className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
                  </div>
                  <span className="font-mono text-[11px] text-[var(--text-muted)]">terminal</span>
                </div>
                <div className="p-4 font-mono text-[13px]">
                  <span className="text-[var(--accent)]">$ </span>
                  <span className="text-[var(--text)]">pip install sigui-sdk</span>
                  <span className="cursor-blink text-[var(--accent)]">|</span>
                </div>
              </div>
            </motion.div>

            {/* Code example */}
            <motion.div
              initial={{ opacity: 0, x: 24 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <CodeBlock code={codeExample} language="python" />
            </motion.div>

            {/* Output snippet */}
            <motion.div
              initial={{ opacity: 0, x: 24 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="border border-[var(--border)] bg-[var(--surface)] rounded-sm p-4 font-mono text-[12px]"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-green)]" />
                <span className="text-[var(--status-green)]">Transaction inspectée — 38ms</span>
              </div>
              <div className="text-[var(--text-muted)]">
                <span className="text-[var(--accent)]">verdict:</span> SAFE — confiance 0.97<br />
                <span className="text-[var(--accent)]">couches:</span> visual ✓ semantic ✓ reputation ✓<br />
                <span className="text-[var(--accent)]">proof:</span> 0x3f4a...c2e1 (Starknet)
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </Section>
  );
}

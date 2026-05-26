import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import { integrations } from "../data";

const categoryLabel: Record<string, string> = {
  framework: "Frameworks",
  chain: "Blockchains",
  hardware: "Hardware",
};

const categoryColor: Record<string, string> = {
  framework: "text-[var(--accent)]",
  chain: "text-[var(--status-green)]",
  hardware: "text-purple-400",
};

export default function EcosystemSection() {
  const categories = ["framework", "chain", "hardware"] as const;

  return (
    <Section id="ecosystem" className="py-48 md:py-64 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="flex flex-col items-center text-center mb-16">
          <SectionTag>Écosystème</SectionTag>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight max-w-xl"
          >
            Intégré partout où<br />
            <span className="font-italic italic text-[var(--accent)]">les agents opèrent.</span>
          </motion.h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--border)]">
          {categories.map((cat, ci) => (
            <motion.div
              key={cat}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: ci * 0.12 }}
              className="bg-[var(--bg)] p-8"
            >
              <div className={`font-mono text-[10px] uppercase tracking-[0.18em] mb-6 ${categoryColor[cat]}`}>
                {categoryLabel[cat]}
              </div>
              <div className="flex flex-col gap-3">
                {integrations
                  .filter((i) => i.category === cat)
                  .map((item, ii) => (
                    <motion.div
                      key={item.name}
                      initial={{ opacity: 0, x: -12 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.4, delay: ci * 0.1 + ii * 0.06 }}
                      className="flex items-center gap-3 group cursor-default"
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${cat === "framework" ? "bg-[var(--accent)]" : cat === "chain" ? "bg-[var(--status-green)]" : "bg-purple-400"}`} />
                      <span className="font-mono text-[13px] text-[var(--text-muted)] group-hover:text-[var(--text)] transition-colors duration-200">
                        {item.name}
                      </span>
                    </motion.div>
                  ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

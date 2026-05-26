import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import { capabilities } from "../data";
import GlowEffect from "./GlowEffect";

export default function CapabilitiesSection() {
  return (
    <Section id="capabilities" className="py-48 md:py-64 px-6">
      <div className="container mx-auto max-w-[1160px]">
        {capabilities.map((cap, i) => {
          const isEven = i % 2 === 0;
          return (
            <div
              key={cap.id}
              className={`flex flex-col ${isEven ? "md:flex-row" : "md:flex-row-reverse"} items-center gap-16 md:gap-32 mb-48 md:mb-64 last:mb-0`}
            >
              {/* Text content */}
              <div className="flex-1 w-full">
                <SectionTag>{cap.tag}</SectionTag>
                <motion.h3
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.72, delay: 0.1 }}
                  className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 mb-6 tracking-tight"
                >
                  {cap.title.split(" ").map((word, idx) => (
                    <span
                      key={idx}
                      className={idx === cap.title.split(" ").length - 1 ? "font-italic italic text-[var(--accent)]" : ""}
                    >
                      {word}{" "}
                    </span>
                  ))}
                </motion.h3>
                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.72, delay: 0.18 }}
                  className="font-mono text-[14px] text-[var(--text-muted)] leading-relaxed mb-8"
                >
                  {cap.description}
                </motion.p>

                <motion.ul
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.25 }}
                  className="space-y-4"
                >
                  {cap.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] opacity-80" />
                      <span className="font-mono text-[12px] text-[var(--text)]">{feature}</span>
                    </li>
                  ))}
                </motion.ul>
              </div>

              {/* Visual representation */}
              <div className="flex-1 w-full relative">
                <GlowEffect className="top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" size={400} color="rgba(235,110,18,0.12)" />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.72, delay: 0.2 }}
                  className="aspect-square md:aspect-[4/3] border border-[var(--border)] bg-[var(--surface)] rounded-sm flex items-center justify-center text-7xl relative overflow-hidden group hover:border-[var(--border-hi)] transition-colors duration-500"
                >
                  <div className="absolute inset-0 bg-gradient-to-tr from-[var(--accent-glow)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                  <span className="relative z-10 group-hover:scale-110 transition-transform duration-500 ease-out">{cap.icon}</span>
                  {/* Decorative background grid */}
                  <div className="absolute inset-0 bg-[linear-gradient(rgba(240,237,230,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(240,237,230,0.03)_1px,transparent_1px)] bg-[size:32px_32px] opacity-20 pointer-events-none" />
                </motion.div>
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

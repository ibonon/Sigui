import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";
import GlowEffect from "./GlowEffect";
import { sahelionStack, operatorVision } from "../data";

export default function SahelionStackSection() {
  return (
    <Section id="sahelion-stack" className="py-48 md:py-64 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        <div className="text-center mb-24">
          <SectionTag>Infrastructure</SectionTag>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl lg:text-6xl text-[var(--text)] mt-6 tracking-tight"
          >
            SAHELION <span className="font-italic italic text-[var(--accent)]">STACK</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.18 }}
            className="font-mono text-[14px] text-[var(--text-muted)] mt-6 max-w-2xl mx-auto leading-relaxed"
          >
            L'infrastructure complète et autonome derrière Sigui Protocol.
            Un réseau P2P natif, alimenté par la cryptographie et l'intelligence artificielle.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
          {/* Left: The Stack */}
          <div className="relative">
            <GlowEffect className="top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" size={500} color="rgba(235,110,18,0.08)" />
            <div className="flex flex-col-reverse gap-3 relative z-10">
              {sahelionStack.map((layer, idx) => (
                <motion.div
                  key={layer.level}
                  initial={{ opacity: 0, x: -24 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: idx * 0.1 }}
                  className="border border-[var(--border)] bg-[var(--surface)] p-5 rounded-sm flex flex-col sm:flex-row sm:items-center gap-4 group hover:border-[var(--accent)]/50 hover:bg-[var(--surface-2)] transition-colors duration-300 relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-[var(--accent-glow)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                  
                  {/* Layer Number */}
                  <div className="flex-shrink-0 w-24">
                    <span className="font-mono text-[10px] text-[var(--accent)] uppercase tracking-widest">{layer.level}</span>
                    <div className="font-mono text-[13px] font-medium text-[var(--text)] mt-1">{layer.name}</div>
                  </div>

                  {/* Divider */}
                  <div className="hidden sm:block w-px h-12 bg-[var(--border)] group-hover:bg-[var(--accent)]/30 transition-colors duration-300" />

                  {/* Content */}
                  <div className="flex-1">
                    <div className="font-mono text-[13px] text-[var(--text)]">{layer.tech}</div>
                    <div className="font-mono text-[11px] text-[var(--text-muted)] mt-1 leading-snug">{layer.desc}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Right: The Vision (Operator Loop) */}
          <div className="relative">
            <GlowEffect className="top-0 right-0" size={400} color="rgba(235,110,18,0.12)" />
            
            <motion.div
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.2 }}
              className="border border-[var(--border)] bg-[var(--surface)] rounded-sm p-8 relative z-10"
            >
              <div className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-widest mb-8 border-b border-[var(--border)] pb-4">
                Vision Opérateur : Économie Agentique
              </div>
              
              <div className="relative">
                {/* Connecting vertical line */}
                <div className="absolute top-4 bottom-4 left-[11px] w-px bg-[var(--border)]" />
                
                <div className="flex flex-col gap-6">
                  {operatorVision.map((step, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: 16 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.4, delay: 0.3 + idx * 0.1 }}
                      className="flex items-start gap-4 relative z-10"
                    >
                      <div className="w-6 h-6 rounded-full bg-[var(--bg)] border border-[var(--accent)] flex items-center justify-center flex-shrink-0 mt-0.5 relative z-10 shadow-[0_0_12px_var(--accent-glow)]">
                        <span className="font-mono text-[10px] text-[var(--accent)]">{idx + 1}</span>
                      </div>
                      <div className="font-mono text-[13px] text-[var(--text)] pt-1">
                        {/* Highlight specific keywords */}
                        {step.split(/(NexusMind|Trustformer|USDC|ERC-8259|économie agentique)/g).map((part, i) => {
                          if (["NexusMind", "Trustformer", "USDC", "ERC-8259", "économie agentique"].includes(part)) {
                            return <span key={i} className="text-[var(--accent)] font-medium">{part}</span>;
                          }
                          return part;
                        })}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Terminal Snippet showing node start */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 1 }}
                className="mt-10 border border-[var(--border)] bg-[var(--surface-2)] rounded-sm p-4 font-mono text-[11px]"
              >
                <div className="text-[var(--text-muted)] mb-2">$ nexusmind start --operator</div>
                <div className="text-[var(--status-green)]">✓ Node joined mesh network</div>
                <div className="text-[var(--text)]">Loading Trustformer model... OK</div>
                <div className="text-[var(--text)]">Waiting for agent transactions...</div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </div>
    </Section>
  );
}

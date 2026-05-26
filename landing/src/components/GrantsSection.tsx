import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";

const grants = [
  {
    name: "Starknet Foundation",
    logo: "⬡",
    color: "#ec796b",
    bgColor: "rgba(236,121,107,0.06)",
    borderColor: "rgba(236,121,107,0.25)",
    status: "active",
    statusLabel: "Candidature active",
    amount: "Up to $500K",
    why: "Contrats Cairo 2.x natifs, ZK-STARK proofs via Halo2, intégration wallet Argent X & Braavos, DePIN oracle network sur Starknet.",
    deliverables: [
      "IAgentReputation.cairo (ERC-8259 on-chain)",
      "IThreatRegistry.cairo (multi-oracle)",
      "Déploiement Sepolia + guide intégration",
    ],
    link: "https://www.starknet.io/en/grants",
  },
  {
    name: "Aptos Foundation",
    logo: "◈",
    color: "#00d9b0",
    bgColor: "rgba(0,217,176,0.06)",
    borderColor: "rgba(0,217,176,0.25)",
    status: "active",
    statusLabel: "Candidature active",
    amount: "Up to $250K",
    why: "Modules Move avec Move Prover (vérification formelle), Block-STM pour la parallélisation, réseau d'oracles IA sur Aptos.",
    deliverables: [
      "agent_reputation.move (specs formelles)",
      "threat_registry.move (multi-oracle)",
      "Tests Move 100% coverage",
    ],
    link: "https://aptosfoundation.org/grants",
  },
  {
    name: "Tether",
    logo: "₮",
    color: "#26a17b",
    bgColor: "rgba(38,161,123,0.06)",
    borderColor: "rgba(38,161,123,0.25)",
    status: "pending",
    statusLabel: "En préparation",
    amount: "TBD",
    why: "Protection des transferts USDC dans l'économie agentique. Modèle économique x402 pay-per-inspection.",
    deliverables: ["SDK x402 complet", "Intégration Circle Wallet", "Métriques de sécurité USDC"],
    link: "#",
  },
  {
    name: "Base (Coinbase)",
    logo: "🔵",
    color: "#0052ff",
    bgColor: "rgba(0,82,255,0.06)",
    borderColor: "rgba(0,82,255,0.25)",
    status: "pending",
    statusLabel: "En préparation",
    amount: "TBD",
    why: "Infrastructure de sécurité pour l'écosystème Coinbase AgentKit et les agents Base chain.",
    deliverables: ["Oracle Base chain", "Intégration AgentKit", "Node DePIN sur Base"],
    link: "#",
  },
];

export default function GrantsSection() {
  return (
    <Section id="grants" className="py-32 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-20">
          <SectionTag>Financement</SectionTag>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight max-w-2xl"
          >
            Partenaires &amp; Subventions.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="font-mono text-[13px] text-[var(--text-muted)] mt-5 max-w-xl leading-relaxed"
          >
            Sigui candidat à plusieurs subventions d'écosystème pour accélérer le déploiement
            de l'infrastructure de sécurité agentique multi-chain.
          </motion.p>
        </div>

        {/* Grant cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
          {grants.map((g, gi) => (
            <motion.div
              key={g.name}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: gi * 0.1 }}
              className="relative rounded-sm overflow-hidden"
              style={{ border: `1px solid ${g.borderColor}`, background: g.bgColor }}
            >
              {/* Status badge */}
              <div className="absolute top-4 right-4">
                <span
                  className="font-mono text-[10px] px-2 py-1 rounded-sm"
                  style={{
                    color: g.color,
                    background: g.bgColor,
                    border: `1px solid ${g.borderColor}`,
                  }}
                >
                  {g.statusLabel}
                </span>
              </div>

              <div className="p-7">
                {/* Logo + name */}
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-sm flex items-center justify-center text-xl font-bold"
                    style={{ background: g.bgColor, border: `1px solid ${g.borderColor}`, color: g.color }}
                  >
                    {g.logo}
                  </div>
                  <div>
                    <div className="font-mono text-[14px] text-[var(--text)] font-medium">{g.name}</div>
                    <div className="font-mono text-[11px]" style={{ color: g.color }}>{g.amount}</div>
                  </div>
                </div>

                {/* Why */}
                <p className="font-mono text-[12px] text-[var(--text-muted)] leading-relaxed mb-5">{g.why}</p>

                {/* Deliverables */}
                <div className="space-y-2">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-2">
                    Livrables
                  </div>
                  {g.deliverables.map((d) => (
                    <div key={d} className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: g.color }} />
                      <span className="font-mono text-[12px] text-[var(--text-muted)]">{d}</span>
                    </div>
                  ))}
                </div>

                {/* Link */}
                {g.link !== "#" && (
                  <motion.a
                    href={g.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ x: 4 }}
                    className="inline-flex items-center gap-1.5 font-mono text-[11px] mt-5"
                    style={{ color: g.color }}
                  >
                    Programme de grants →
                  </motion.a>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom call-out */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="border border-[var(--border)] bg-[var(--surface)] rounded-sm p-8 flex flex-col md:flex-row items-center justify-between gap-6"
        >
          <div>
            <div className="font-mono text-[13px] text-[var(--text)] font-medium mb-1">
              Intéressé par un partenariat ?
            </div>
            <p className="font-mono text-[12px] text-[var(--text-muted)]">
              Sigui cherche des partenaires d'écosystème, des co-investisseurs et des opérateurs de nœuds.
            </p>
          </div>
          <motion.a
            href="mailto:eric@sigui.io"
            whileHover={{ scale: 1.03, boxShadow: "0 0 24px rgba(235,110,18,0.3)" }}
            whileTap={{ scale: 0.97 }}
            className="flex-shrink-0 font-mono text-[13px] text-[var(--bg)] bg-[var(--accent)] px-5 py-2.5 rounded-sm font-medium"
          >
            Nous contacter →
          </motion.a>
        </motion.div>
      </div>
    </Section>
  );
}

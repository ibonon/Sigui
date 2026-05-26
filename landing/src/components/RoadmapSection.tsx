import { motion } from "framer-motion";
import Section from "./Section";
import SectionTag from "./SectionTag";

const milestones = [
  {
    quarter: "Q1 2026",
    status: "done",
    items: [
      { label: "Dataset Sigui-DePIN-1M généré (1.87M txs réelles)", done: true },
      { label: "Imina-Na V2 — Fine-tuning LoRA sur Qwen2-VL-2B", done: true },
      { label: "SDK Python v0.3 publié sur PyPI", done: true },
      { label: "Intégrations LangChain / CrewAI / AutoGen / LangGraph", done: true },
    ],
  },
  {
    quarter: "Q2 2026",
    status: "active",
    items: [
      { label: "Contrats Cairo 2.x sur Starknet Sepolia Testnet", done: false, chain: "starknet" },
      { label: "Contrats Move sur Aptos Testnet (Move Prover specs)", done: false, chain: "aptos" },
      { label: "Mock API server embarqué dans le SDK", done: false },
      { label: "Intégration ElizaOS + mode from_pretrained", done: false },
      { label: "Whitepaper Trustformer (T-GAT) — soumission arXiv", done: false },
    ],
  },
  {
    quarter: "Q3 2026",
    status: "planned",
    items: [
      { label: "Trustformer — Entraînement architecture T-GAT", done: false },
      { label: "ZK-STARK proofs — circuit Giza / Halo2", done: false },
      { label: "Dashboard temps réel (WebSockets + D3.js Network Map)", done: false },
      { label: "Déploiement Starknet Mainnet (post-audit)", done: false, chain: "starknet" },
    ],
  },
  {
    quarter: "Q4 2026",
    status: "planned",
    items: [
      { label: "Aptos Mainnet — DePIN node network live", done: false, chain: "aptos" },
      { label: "OpenRouter — Imina-Na V2 comme provider public", done: false },
      { label: "Soumission NeurIPS / ICML (Trustformer paper)", done: false },
      { label: "Ecosystem: Ethereum, Arbitrum, Base, Polygon oracles", done: false },
    ],
  },
];

const statusConfig = {
  done:    { label: "Complété",    dot: "bg-[var(--status-green)]", line: "border-[var(--status-green)]", text: "text-[var(--status-green)]" },
  active:  { label: "En cours",   dot: "bg-[var(--accent)] animate-pulse", line: "border-[var(--accent)]", text: "text-[var(--accent)]" },
  planned: { label: "Planifié",   dot: "bg-[var(--border-hi)]", line: "border-[var(--border-hi)]", text: "text-[var(--text-muted)]" },
};

const chainBadge: Record<string, string> = {
  starknet: "bg-[#ec796b]/10 text-[#ec796b] border border-[#ec796b]/30",
  aptos:    "bg-[#00d9b0]/10 text-[#00d9b0] border border-[#00d9b0]/30",
};
const chainLabel: Record<string, string> = {
  starknet: "Starknet",
  aptos:    "Aptos",
};

export default function RoadmapSection() {
  return (
    <Section id="roadmap" className="py-32 px-6 border-t border-[var(--border)]">
      <div className="container mx-auto max-w-[1160px]">
        {/* Header */}
        <div className="flex flex-col items-center text-center mb-20">
          <SectionTag>Roadmap</SectionTag>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-4xl md:text-5xl text-[var(--text)] mt-6 tracking-tight max-w-2xl"
          >
            Construit pour durer.<br />
            <span className="font-italic italic text-[var(--accent)]">Financé pour accélérer.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="font-mono text-[13px] text-[var(--text-muted)] mt-5 max-w-xl leading-relaxed"
          >
            Candidatures actives : <span className="text-[#ec796b]">Starknet Foundation</span> · <span className="text-[#00d9b0]">Aptos Foundation</span> · Tether · Base · Polygon
          </motion.p>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-px bg-[var(--border)] -translate-x-1/2 hidden md:block" />

          <div className="space-y-12">
            {milestones.map((m, mi) => {
              const cfg = statusConfig[m.status as keyof typeof statusConfig];
              const isLeft = mi % 2 === 0;
              return (
                <motion.div
                  key={m.quarter}
                  initial={{ opacity: 0, y: 28 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: mi * 0.1 }}
                  className={`flex flex-col md:flex-row gap-8 ${isLeft ? "md:flex-row" : "md:flex-row-reverse"}`}
                >
                  {/* Card */}
                  <div className="md:w-[calc(50%-2rem)]">
                    <div className={`border rounded-sm p-6 bg-[var(--surface)] ${m.status === "active" ? "border-[var(--accent)]/30" : "border-[var(--border)]"}`}>
                      {/* Quarter header */}
                      <div className="flex items-center justify-between mb-5">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                          <span className={`font-mono text-[11px] uppercase tracking-widest ${cfg.text}`}>{m.quarter}</span>
                        </div>
                        <span className={`font-mono text-[10px] px-2 py-0.5 rounded-sm border ${cfg.line} ${cfg.text} border-opacity-30`}>
                          {cfg.label}
                        </span>
                      </div>
                      {/* Items */}
                      <ul className="space-y-2.5">
                        {m.items.map((item, ii) => (
                          <li key={ii} className="flex items-start gap-2.5">
                            <span className={`mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full ${item.done ? "bg-[var(--status-green)]" : "bg-[var(--border-hi)]"}`} />
                            <span className={`font-mono text-[12px] leading-relaxed ${item.done ? "text-[var(--text-muted)] line-through" : "text-[var(--text-muted)]"}`}>
                              {item.label}
                            </span>
                            {item.chain && (
                              <span className={`flex-shrink-0 font-mono text-[9px] px-1.5 py-0.5 rounded-sm ${chainBadge[item.chain]}`}>
                                {chainLabel[item.chain]}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Center dot (desktop) */}
                  <div className="hidden md:flex items-center justify-center w-16 flex-shrink-0">
                    <div className={`w-3 h-3 rounded-full border-2 ${m.status === "active" ? "border-[var(--accent)] bg-[var(--accent)]/20" : m.status === "done" ? "border-[var(--status-green)] bg-[var(--status-green)]/20" : "border-[var(--border-hi)] bg-[var(--bg)]"}`} />
                  </div>

                  {/* Spacer */}
                  <div className="md:w-[calc(50%-2rem)]" />
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Grant badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-20 flex flex-wrap justify-center gap-4"
        >
          {[
            { name: "Starknet Foundation", color: "#ec796b", status: "Candidature active" },
            { name: "Aptos Foundation",    color: "#00d9b0", status: "Candidature active" },
            { name: "Tether",              color: "#26a17b", status: "En préparation" },
            { name: "Base",                color: "#0052ff", status: "En préparation" },
            { name: "Polygon",             color: "#8247e5", status: "En préparation" },
          ].map((g) => (
            <div
              key={g.name}
              className="flex items-center gap-2.5 border border-[var(--border)] rounded-sm px-4 py-2.5 bg-[var(--surface)]"
            >
              <div className="w-2 h-2 rounded-full" style={{ background: g.color }} />
              <span className="font-mono text-[12px] text-[var(--text)]">{g.name}</span>
              <span className="font-mono text-[10px] text-[var(--text-muted)]">— {g.status}</span>
            </div>
          ))}
        </motion.div>
      </div>
    </Section>
  );
}

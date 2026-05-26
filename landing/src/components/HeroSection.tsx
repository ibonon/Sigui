import { useState } from "react";
import { motion } from "framer-motion";
import GlowEffect from "./GlowEffect";

export default function HeroSection() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText("pip install sigui-sdk");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center pt-32 pb-48 md:pt-48 md:pb-64 overflow-hidden">
      {/* Animated grid */}
      <div className="hero-grid" aria-hidden="true" />

      {/* Ambient glows */}
      <GlowEffect className="-top-40 left-1/2 -translate-x-1/2" size={700} />
      <GlowEffect className="top-1/2 -left-40 -translate-y-1/2" size={400} color="rgba(235,110,18,0.10)" />
      <GlowEffect className="top-1/2 -right-40 -translate-y-1/2" size={400} color="rgba(235,110,18,0.10)" />

      <div className="container mx-auto max-w-[1160px] px-6 text-center relative z-10">
        {/* Status badge */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="inline-flex items-center gap-2 font-mono text-[11px] border border-[var(--border)] text-[var(--text-muted)] px-3 py-1.5 rounded-sm mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-green)] animate-pulse" />
          Oracle de sécurité actif — réseau Starknet & Ethereum
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="font-mono text-[11px] uppercase tracking-[0.22em] text-[var(--accent)] mb-5"
        >
          Infrastructure de sécurité pour agents IA
        </motion.p>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.72, delay: 0.2 }}
          className="font-display text-5xl md:text-7xl lg:text-8xl text-[var(--text)] leading-[0.95] tracking-tight mb-6 max-w-5xl mx-auto"
        >
          Votre agent IA<br />
          <span className="font-italic italic text-[var(--accent)]">n'est pas à l'abri.</span>
          <br />
          Jusqu'à aujourd'hui.
        </motion.h1>

        {/* Sub-headline */}
        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.72, delay: 0.28 }}
          className="font-mono text-[13px] text-[var(--text-muted)] leading-relaxed max-w-2xl mx-auto mb-10"
        >
          Sigui est un oracle de sécurité décentralisé qui inspecte chaque transaction en{" "}
          <span className="text-[var(--text)]">moins de 50ms</span>, avant qu'elle ne soit exécutée.
          Détection visuelle multimodale, preuves ZK-STARK, réputation on-chain.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.72, delay: 0.35 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        >
          {/* Primary CTA */}
          <motion.a
            href="https://github.com/ibonon/Sigui"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.03, boxShadow: "0 0 36px rgba(235,110,18,0.4)" }}
            whileTap={{ scale: 0.97 }}
            className="font-mono text-[13px] text-[var(--bg)] bg-[var(--accent)] px-6 py-3 rounded-sm font-medium transition-all duration-300"
          >
            Installer le SDK →
          </motion.a>

          {/* Install snippet */}
          <motion.button
            onClick={handleCopy}
            whileHover={{ scale: 1.02, borderColor: "rgba(240,237,230,0.22)" }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-3 font-mono text-[13px] text-[var(--text-muted)] border border-[var(--border)] px-5 py-3 rounded-sm hover:text-[var(--text)] transition-all duration-200 group"
          >
            <span className="text-[var(--accent)]">$</span>
            <span>pip install sigui-sdk</span>
            <span className={`text-[11px] ml-1 transition-colors duration-200 ${copied ? "text-[var(--status-green)]" : "text-[var(--border-hi)] group-hover:text-[var(--text-muted)]"}`}>
              {copied ? "✓ copié" : "⌘C"}
            </span>
          </motion.button>
        </motion.div>

        {/* Floating visual */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.45 }}
          className="relative max-w-4xl mx-auto"
          style={{ animation: "float 6s ease-in-out infinite" }}
        >
          <div className="border border-[var(--border)] bg-[var(--surface)] rounded-sm overflow-hidden relative">
            {/* Mock dashboard */}
            <div className="border-b border-[var(--border)] bg-[var(--surface-2)] px-5 py-3 flex items-center gap-3">
              <div className="flex gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              </div>
              <span className="font-mono text-[11px] text-[var(--text-muted)]">sigui — live inspector</span>
              <span className="ml-auto font-mono text-[11px] text-[var(--status-green)] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-green)] animate-pulse" />
                LIVE
              </span>
            </div>
            <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Metric mini-cards */}
              {[
                { label: "Transactions inspectées", value: "2,847,291", color: "text-[var(--text)]" },
                { label: "Attaques bloquées", value: "1,204", color: "text-red-400" },
                { label: "Latence moyenne", value: "38ms", color: "text-[var(--status-green)]" },
              ].map((m) => (
                <div key={m.label} className="border border-[var(--border)] rounded-sm p-3 bg-[var(--bg)]">
                  <div className={`font-mono text-xl font-bold ${m.color}`}>{m.value}</div>
                  <div className="font-mono text-[11px] text-[var(--text-muted)] mt-1">{m.label}</div>
                </div>
              ))}
            </div>
            {/* Animated risk pipeline bar */}
            <div className="px-5 pb-5">
              <div className="border border-[var(--border)] rounded-sm p-4 bg-[var(--bg)]">
                <div className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-widest mb-3">
                  Risk Pipeline — dernière transaction
                </div>
                <div className="flex items-center gap-2">
                  {["Visual", "Semantic", "Reputation", "ZK", "Verdict"].map((step, i) => (
                    <div key={step} className="flex items-center gap-2 flex-1">
                      <div className="flex-1 h-1.5 rounded-full bg-[var(--accent)] pipeline-bar" style={{ animationDelay: `${i * 0.12}s` }} />
                      <span className="font-mono text-[9px] text-[var(--text-muted)] whitespace-nowrap">{step}</span>
                    </div>
                  ))}
                  <span className="font-mono text-[11px] text-[var(--status-green)] ml-2">✓ SAFE</span>
                </div>
              </div>
            </div>
          </div>
          {/* Glow under card */}
          <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-[var(--accent)] opacity-10 blur-3xl rounded-full pointer-events-none" />
        </motion.div>
      </div>
    </section>
  );
}

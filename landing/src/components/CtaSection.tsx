import { useState } from "react";
import { motion } from "framer-motion";
import GlowEffect from "./GlowEffect";

export default function CtaSection() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) setSubmitted(true);
  };

  return (
    <section id="cta" className="relative py-48 md:py-64 px-6 border-t border-[var(--border)] overflow-hidden">
      <GlowEffect className="top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" size={800} color="rgba(235,110,18,0.12)" />

      <div className="container mx-auto max-w-[1160px] relative z-10">
        <div className="text-center">
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-[var(--accent)] mb-5"
          >
            Passez à l'action
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.1 }}
            className="font-display text-5xl md:text-7xl text-[var(--text)] tracking-tight mb-6 max-w-3xl mx-auto"
          >
            Prêt à sécuriser<br />
            <span className="font-italic italic text-[var(--accent)]">vos agents ?</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.18 }}
            className="font-mono text-[13px] text-[var(--text-muted)] mb-12 max-w-lg mx-auto leading-relaxed"
          >
            Open-source, MIT. Déployez Sigui en moins de 5 minutes.
            Rejoignez la communauté de développeurs qui sécurisent leurs agents IA.
          </motion.p>

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.72, delay: 0.25 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
          >
            <motion.a
              href="https://pypi.org/project/sigui-sdk/"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.03, boxShadow: "0 0 48px rgba(235,110,18,0.45)" }}
              whileTap={{ scale: 0.97 }}
              className="font-mono text-[14px] text-[var(--bg)] bg-[var(--accent)] px-8 py-3.5 rounded-sm font-medium transition-all duration-300"
            >
              Installer le SDK
            </motion.a>
            <motion.a
              href="https://github.com/ibonon/Sigui"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.02, borderColor: "rgba(240,237,230,0.22)" }}
              whileTap={{ scale: 0.97 }}
              className="font-mono text-[14px] text-[var(--text-muted)] border border-[var(--border)] px-8 py-3.5 rounded-sm hover:text-[var(--text)] transition-all duration-200"
            >
              Voir sur GitHub →
            </motion.a>
          </motion.div>

          {/* Email capture */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="max-w-md mx-auto"
          >
            {submitted ? (
              <div className="flex items-center justify-center gap-2 font-mono text-[13px] text-[var(--status-green)] border border-[var(--status-green)]/30 px-5 py-3 rounded-sm bg-[var(--status-green)]/5">
                <span>✓</span>
                <span>Vous serez notifié des mises à jour de Sigui.</span>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex gap-0">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="votre@email.com"
                  className="flex-1 font-mono text-[13px] text-[var(--text)] bg-[var(--surface)] border border-[var(--border)] border-r-0 px-4 py-3 rounded-l-sm placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--border-hi)] transition-colors duration-200"
                />
                <button
                  type="submit"
                  className="font-mono text-[12px] text-[var(--bg)] bg-[var(--accent)] px-5 py-3 rounded-r-sm hover:opacity-90 transition-opacity duration-200 whitespace-nowrap"
                >
                  Recevoir les updates
                </button>
              </form>
            )}
            <p className="font-mono text-[11px] text-[var(--text-muted)] mt-3 opacity-60">
              Pas de spam. Mises à jour de recherche et releases uniquement.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

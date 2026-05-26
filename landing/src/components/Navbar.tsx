import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { navLinks } from "../data";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleInstall = () => {
    navigator.clipboard.writeText("pip install sigui-sdk");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-[var(--border)] bg-[var(--bg)]/80 backdrop-blur-md">
      <div className="container mx-auto max-w-[1160px] px-6 h-full flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-sm bg-[var(--accent)] flex items-center justify-center relative overflow-hidden">
            <span className="font-mono font-bold text-sm text-[var(--bg)]">S</span>
            <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <span className="font-mono text-[13px] text-[var(--text)] tracking-tight">
            Sigui<span className="text-[var(--accent)]">Protocol</span>
          </span>
        </a>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="font-mono text-[13px] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors duration-200"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <motion.button
            onClick={handleInstall}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-2 font-mono text-[12px] text-[var(--text-muted)] border border-[var(--border)] px-3 py-1.5 rounded-sm hover:border-[var(--border-hi)] transition-all duration-200"
          >
            <span className="text-[var(--accent)]">$</span>
            <span>pip install sigui-sdk</span>
            <AnimatePresence mode="wait">
              <motion.span
                key={copied ? "copied" : "copy"}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={`ml-1 text-[10px] ${copied ? "text-[var(--status-green)]" : "text-[var(--text-muted)]"}`}
              >
                {copied ? "✓" : "⌘C"}
              </motion.span>
            </AnimatePresence>
          </motion.button>
          <motion.a
            href="https://github.com/ibonon/Sigui"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.02, boxShadow: "0 0 28px var(--accent-glow)" }}
            whileTap={{ scale: 0.97 }}
            className="font-mono text-[12px] text-[var(--bg)] bg-[var(--accent)] px-4 py-1.5 rounded-sm font-medium transition-all duration-200"
          >
            GitHub →
          </motion.a>
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setOpen(!open)}
          className="md:hidden font-mono text-[13px] text-[var(--text-muted)]"
        >
          {open ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="md:hidden border-t border-[var(--border)] bg-[var(--bg)] px-6 py-4 flex flex-col gap-4"
          >
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="font-mono text-[13px] text-[var(--text-muted)] hover:text-[var(--text)]"
                onClick={() => setOpen(false)}
              >
                {link.label}
              </a>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

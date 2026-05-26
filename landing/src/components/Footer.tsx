import { footerLinks } from "../data";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--surface-2)] px-6 py-12">
      <div className="container mx-auto max-w-[1160px]">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Brand */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-sm bg-[var(--accent)] flex items-center justify-center">
                <span className="font-mono font-bold text-xs text-[var(--bg)]">S</span>
              </div>
              <span className="font-mono text-[13px] text-[var(--text)]">
                Sigui<span className="text-[var(--accent)]">Protocol</span>
              </span>
            </div>
            <p className="font-mono text-[11px] text-[var(--text-muted)] max-w-xs leading-relaxed">
              Oracle de sécurité décentralisé pour agents IA. Open-source, MIT.
            </p>
          </div>

          {/* Links */}
          <nav className="flex flex-wrap gap-x-6 gap-y-3">
            {footerLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[12px] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors duration-200"
              >
                {link.label}
              </a>
            ))}
          </nav>
        </div>

        <div className="mt-10 pt-6 border-t border-[var(--border)] flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="font-mono text-[11px] text-[var(--text-muted)]">
            © 2026 Sigui Protocol — Open Source (MIT)
          </p>
          <p className="font-mono text-[11px] text-[var(--text-muted)]">
            ERC-8259 · ZK-STARK · Imina-Na V2
          </p>
        </div>
      </div>
    </footer>
  );
}

import { useState } from "react";
import { motion } from "framer-motion";

interface CodeBlockProps {
  code: string;
  language?: string;
  copyable?: boolean;
}

export default function CodeBlock({ code, language = "python", copyable = true }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group border border-[var(--border)] bg-[var(--surface)] rounded-sm overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--border)] bg-[var(--surface-2)]">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
        </div>
        <span className="font-mono text-[11px] text-[var(--text-muted)] uppercase tracking-widest">
          {language}
        </span>
        {copyable && (
          <motion.button
            onClick={handleCopy}
            whileTap={{ scale: 0.95 }}
            className="font-mono text-[11px] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors duration-200 flex items-center gap-1.5"
          >
            {copied ? (
              <>
                <span className="text-[var(--status-green)]">✓</span>
                <span className="text-[var(--status-green)]">Copié</span>
              </>
            ) : (
              <>
                <span>⌘</span>
                <span>Copier</span>
              </>
            )}
          </motion.button>
        )}
      </div>
      {/* Code area */}
      <pre className="p-5 overflow-x-auto font-mono text-[13px] text-[var(--text)] leading-relaxed whitespace-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}

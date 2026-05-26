import { motion, useInView } from "framer-motion";
import { useRef } from "react";

interface SectionProps {
  id?: string;
  className?: string;
  children: React.ReactNode;
}

export default function Section({ id, className = "", children }: SectionProps) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.section
      id={id}
      ref={ref}
      className={`relative ${className}`}
      initial={{ opacity: 0, y: 32 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.72, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.section>
  );
}

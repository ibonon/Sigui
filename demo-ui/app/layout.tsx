import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ArcWarden — Autonomous Security Oracle",
  description: "Real-time AI-powered threat detection, x402 payment loop, Circle DCW treasury. Hackathon: Agentic Economy on ARC.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


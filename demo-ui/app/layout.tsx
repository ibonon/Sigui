import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sigui Protocol — The Regeneration Oracle",
  description:
    "Omnichain visual security oracle with Imina Na, Kanaga, Hogonat DAO and multi-chain treasury dashboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


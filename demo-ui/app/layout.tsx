import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CRTOverlay } from "./components/CRTOverlay";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sigui | NexusMind",
  description: "Autonomous Security and P2P Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CRTOverlay />
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FrameGuard | Frame-level video tamper detection",
  description:
    "Break a video into frames, hash each with SHA-256, anchor one Merkle root, and localize exactly which frames were tampered.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}

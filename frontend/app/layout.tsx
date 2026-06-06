import type { Metadata } from "next";
import GrainOverlay from "@/components/GrainOverlay";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deep Research Platform",
  description: "Multi-agent research with web search, fact checking, and human approval gates.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <GrainOverlay />
        <main style={{ minHeight: "100vh", display: "flex", flexDirection: "column", position: "relative", zIndex: 1 }}>
          {children}
        </main>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import { AppWrapper } from "@/components/layout/AppWrapper";

export const metadata: Metadata = {
  title: "AURA AI — Autonomous Universal Reasoning Agent",
  description:
    "Advanced AI Operating System with intelligent routing, memory, and tool usage. Powered by cloud LLMs.",
  keywords: ["AI", "Operating System", "LLM", "Gemini", "Chat", "AURA"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <AppWrapper>
          {children}
        </AppWrapper>
      </body>
    </html>
  );
}

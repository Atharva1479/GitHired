import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { PilotShell } from "./PilotShell";
import { Providers } from "./providers";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "GitHired — Track your job hunt",
  description:
    "Track applications and referrals. Get the right nudge at the right time. Never lose a follow-up.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-[var(--color-bg)] text-[var(--color-text)]">
        <ErrorBoundary>
          <Providers>
            {children}
            {/* PilotShell mounts the voice agent above page boundaries so
                its state survives route changes. */}
            <PilotShell />
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}

"use client";

import { usePathname } from "next/navigation";

import { PilotOrb } from "@/components/pilot/PilotOrb";

/**
 * Mounts the voice agent once at the root layout level so its state
 * (conversation history, recording status, voice-mode open/closed)
 * survives every client-side route change.
 *
 * Skipped on /login and the empty / route where the user isn't
 * authenticated — those pages don't render the rest of the app shell.
 */
export function PilotShell() {
  const pathname = usePathname();
  if (pathname === "/login" || pathname === "/" || pathname === "/interview/session") return null;
  return <PilotOrb />;
}

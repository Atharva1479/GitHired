"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { CelebrationLayer } from "@/components/gamify/CelebrationLayer";
import { FloatingXp } from "@/components/gamify/FloatingXp";
import { useGamifyAutoRefresh } from "@/hooks/useGamify";
import { useMe } from "@/hooks/useMe";
import { ApiError } from "@/lib/api";

import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: ReactNode }) {
  const { data: me, isLoading, error } = useMe();
  const router = useRouter();
  useGamifyAutoRefresh();

  const unauthorized = error instanceof ApiError && error.status === 401;

  useEffect(() => {
    if (unauthorized) router.replace("/login");
  }, [unauthorized, router]);

  if (isLoading || unauthorized || !me) {
    return (
      <div className="min-h-[60dvh] grid place-items-center">
        <div className="h-9 w-9 rounded-full border-2 border-[var(--color-border)] border-t-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <TopBar />
      {children}
      <FloatingXp />
      <CelebrationLayer />
      {/* PilotOrb now lives at the root layout (see app/PilotShell.tsx)
          so it survives client-side navigation. */}
    </>
  );
}

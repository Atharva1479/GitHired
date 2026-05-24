"use client";

import { Crown, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useGamifyState } from "@/hooks/useGamify";
import type { GamifyEnvelope } from "@/lib/api";
import { rankForLevel } from "@/lib/rank";

export function XpBar() {
  const { data } = useGamifyState();
  const [pulsing, setPulsing] = useState(false);
  const pulseTimer = useRef<number | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const env = (e as CustomEvent<GamifyEnvelope>).detail;
      if (!env || env.xp_gained <= 0) return;
      // Fire pulse only after the XP particle has landed (~1.1s flight).
      window.setTimeout(() => {
        setPulsing(true);
        if (pulseTimer.current) window.clearTimeout(pulseTimer.current);
        pulseTimer.current = window.setTimeout(
          () => setPulsing(false),
          700,
        );
      }, 950);
    };
    window.addEventListener("jp:gamify", handler);
    return () => {
      window.removeEventListener("jp:gamify", handler);
      if (pulseTimer.current) window.clearTimeout(pulseTimer.current);
    };
  }, []);

  if (!data) return null;

  const span = data.xp_for_level || 1;
  const pct = Math.min(100, Math.round((data.xp_into_level / span) * 100));
  const rank = rankForLevel(data.level);
  const nearFull = pct >= 80;

  return (
    <Link
      href="/achievements"
      data-xp-target="1"
      aria-label={`Level ${data.level} — ${rank.title}. ${data.xp_into_level}/${data.xp_for_level} XP`}
      className={`group relative hidden md:flex items-center gap-2 rounded-full px-1.5 py-1 ring-1 ring-[var(--color-border)] hover:ring-[var(--color-border-2)] hover:bg-[var(--color-surface-2)] transition-all ${
        pulsing ? "pulse-glow" : ""
      }`}
    >
      <span
        className={`relative grid place-items-center w-6 h-6 rounded-full text-[11px] font-bold tabular-nums ring-1 ${rank.badge}`}
      >
        {data.level >= 5 ? (
          <Crown className="absolute -top-2.5 w-3.5 h-3.5 text-yellow-500 drop-shadow" />
        ) : null}
        {data.level}
      </span>
      <div className="relative w-28 h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
        {nearFull ? (
          <div
            className="absolute inset-y-0 left-0 shimmer-bar rounded-full"
            style={{ width: `${pct}%` }}
          />
        ) : null}
      </div>
      <Zap
        className={`w-3.5 h-3.5 transition-colors ${
          pulsing ? "text-fuchsia-500" : "text-gray-400"
        }`}
      />

      <div className="absolute top-full right-0 mt-1.5 hidden group-hover:block z-40 pointer-events-none">
        <div className="rounded-lg bg-gray-900 text-white text-[11.5px] px-3 py-2 whitespace-nowrap shadow-xl">
          <div className="flex items-center gap-1.5 font-semibold text-[12px]">
            {data.level >= 5 ? (
              <Crown className="w-3 h-3 text-yellow-400" />
            ) : null}
            Level {data.level} · {rank.title}
          </div>
          <div className="mt-0.5 text-[11px] text-gray-300 tabular-nums">
            {data.xp_into_level}/{data.xp_for_level} XP to level {data.level + 1}
          </div>
        </div>
      </div>
    </Link>
  );
}

"use client";

import { Flame } from "lucide-react";

import { useGamifyState } from "@/hooks/useGamify";

type Tier = {
  label: string;
  flameClass: string;
  glowClass: string;
  ringClass: string;
  embers: number;
  inferno: boolean;
};

function tierFor(streak: number): Tier {
  if (streak >= 30) {
    return {
      label: "Blue flame",
      flameClass: "text-cyan-400 drop-shadow-[0_0_8px_rgba(56,189,248,0.7)]",
      glowClass: "bg-cyan-400/30",
      ringClass: "ring-cyan-300/60",
      embers: 5,
      inferno: true,
    };
  }
  if (streak >= 14) {
    return {
      label: "Inferno",
      flameClass: "text-red-500 drop-shadow-[0_0_6px_rgba(248,113,113,0.6)]",
      glowClass: "bg-red-400/30",
      ringClass: "ring-red-300/60",
      embers: 4,
      inferno: true,
    };
  }
  if (streak >= 7) {
    return {
      label: "On fire",
      flameClass: "text-orange-500 drop-shadow-[0_0_5px_rgba(249,115,22,0.55)]",
      glowClass: "bg-orange-400/25",
      ringClass: "ring-orange-300/60",
      embers: 3,
      inferno: false,
    };
  }
  if (streak >= 3) {
    return {
      label: "Heating up",
      flameClass: "text-orange-500",
      glowClass: "bg-amber-300/20",
      ringClass: "ring-amber-200/60",
      embers: 2,
      inferno: false,
    };
  }
  return {
    label: "Streak",
    flameClass: "text-amber-500",
    glowClass: "bg-amber-200/15",
    ringClass: "ring-amber-200/40",
    embers: 0,
    inferno: false,
  };
}

function nextMilestone(streak: number): number {
  for (const m of [3, 7, 14, 30, 100]) {
    if (streak < m) return m;
  }
  return streak + 1;
}

export function StreakFlame() {
  const { data } = useGamifyState();
  if (!data || data.streak === 0) return null;

  const tier = tierFor(data.streak);
  const next = nextMilestone(data.streak);
  const toGo = next - data.streak;

  return (
    <div
      className="group relative inline-flex items-center gap-1 px-2 py-1 rounded-full hover:bg-[var(--color-surface-2)] transition-colors"
      aria-label={`${data.streak}-day streak — ${tier.label}`}
    >
      <span className="relative grid place-items-center w-5 h-5">
        <span
          className={`absolute inset-0 rounded-full ${tier.glowClass} aura-breathe`}
          aria-hidden
        />
        <Flame
          className={`relative w-4 h-4 ${tier.flameClass} ${tier.inferno ? "flame-flicker" : ""}`}
        />
        {/* ember particles */}
        {tier.embers > 0 ? (
          <span className="absolute inset-0 pointer-events-none" aria-hidden>
            {Array.from({ length: tier.embers }).map((_, i) => (
              <span
                key={i}
                className={`absolute w-0.5 h-0.5 rounded-full ember-rise ${tier.flameClass.split(" ")[0]}`}
                style={{
                  left: `${30 + i * 12}%`,
                  bottom: "20%",
                  animationDelay: `${i * 0.3}s`,
                  backgroundColor: "currentColor",
                  opacity: 0.7,
                }}
              />
            ))}
          </span>
        ) : null}
      </span>
      <span className="text-[13px] font-bold tabular-nums text-[var(--color-text)]">
        {data.streak}
      </span>

      <div className="absolute top-full right-0 mt-1.5 hidden group-hover:block z-40 pointer-events-none">
        <div className="rounded-lg bg-gray-900 text-white text-[11.5px] px-3 py-2 whitespace-nowrap shadow-xl">
          <div className="flex items-center gap-1.5 text-[12px] font-semibold">
            <Flame className={`w-3 h-3 ${tier.flameClass.split(" ")[0]}`} />
            {data.streak}-day streak · {tier.label}
          </div>
          <div className="mt-0.5 text-[11px] text-gray-300 tabular-nums">
            {toGo} day{toGo === 1 ? "" : "s"} to next milestone
          </div>
          <div className="mt-0.5 text-[11px] text-gray-400">
            {data.freezes} freeze{data.freezes === 1 ? "" : "s"} banked · longest {data.longest_streak}d
          </div>
        </div>
      </div>
    </div>
  );
}

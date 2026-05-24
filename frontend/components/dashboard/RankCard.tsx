"use client";

import Link from "next/link";
import { useGamifyState } from "@/hooks/useGamify";
import { rankForLevel } from "@/lib/rank";

const TIER_EMOJI: Record<string, string> = {
  bronze:   "🥉",
  silver:   "🥈",
  gold:     "🥇",
  platinum: "💎",
  diamond:  "💠",
  master:   "👑",
};

export function RankCard() {
  const { data } = useGamifyState();
  if (!data) return null;

  const rank = rankForLevel(data.level);
  const pct = data.xp_for_level > 0
    ? Math.round((data.xp_into_level / data.xp_for_level) * 100)
    : 0;
  const emoji = TIER_EMOJI[rank.tier] ?? "⭐";

  return (
    <Link href="/achievements" className="block">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 hover:border-[#9080e0]/40 transition-colors">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#6b50c0] to-[#9060d0] grid place-items-center text-xl shrink-0">
            {emoji}
          </div>
          <div>
            <div className="text-[13.5px] font-bold text-[var(--color-text)]">
              {rank.title}
            </div>
            <div className="text-[11px] text-[var(--color-text-3)] mt-0.5">
              Level {data.level} · {data.xp_for_level - data.xp_into_level} XP to next
            </div>
          </div>
        </div>
        <div className="h-1 bg-[var(--color-surface-2)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-[width] duration-700"
            style={{
              width: `${pct}%`,
              background: "linear-gradient(90deg, #7040c0, #9060d0)",
            }}
          />
        </div>
        <div className="flex justify-between mt-1.5 text-[10px] text-[var(--color-text-3)]">
          <span>{data.xp_into_level} XP</span>
          <span className="text-[#9080e0]">{data.xp_for_level} XP</span>
        </div>
      </div>
    </Link>
  );
}

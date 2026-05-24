"use client";

import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { Crown, Lock, Sparkles, Trophy } from "lucide-react";
import { useMemo, useRef, type MouseEvent } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { useAchievements, useGamifyState } from "@/hooks/useGamify";
import {
  type AchievementMeta,
  TIER_CLASSES,
  metaFor,
} from "@/lib/achievements";
import type { Achievement } from "@/lib/api";
import { rankForLevel } from "@/lib/rank";

type Row = {
  meta: AchievementMeta;
  unlocked_at: string | null;
};

const GROUP_ORDER: AchievementMeta["group"][] = [
  "volume",
  "pipeline",
  "streak",
  "network",
  "comeback",
];

const GROUP_LABEL: Record<AchievementMeta["group"], string> = {
  volume: "Volume",
  pipeline: "Pipeline",
  streak: "Consistency",
  network: "Network",
  comeback: "Resilience",
};

const GROUP_ACCENT: Record<AchievementMeta["group"], string> = {
  volume: "from-indigo-500 to-violet-500",
  pipeline: "from-amber-500 to-orange-500",
  streak: "from-rose-500 to-red-500",
  network: "from-emerald-500 to-teal-500",
  comeback: "from-cyan-500 to-sky-500",
};

export default function AchievementsPage() {
  const { data, isLoading } = useAchievements();
  const state = useGamifyState();

  const rows: Row[] = useMemo(
    () =>
      (data ?? []).map((a: Achievement) => ({
        meta: metaFor(a.code),
        unlocked_at: a.unlocked_at,
      })),
    [data],
  );

  const unlockedCount = rows.filter((r) => r.unlocked_at).length;
  const total = rows.length;
  const overallPct = total > 0 ? Math.round((unlockedCount / total) * 100) : 0;
  const mostRecent = useMemo(() => {
    return rows
      .filter((r) => r.unlocked_at)
      .sort((a, b) =>
        (b.unlocked_at ?? "").localeCompare(a.unlocked_at ?? ""),
      )[0];
  }, [rows]);

  const grouped = useMemo(() => {
    const map = new Map<AchievementMeta["group"], Row[]>();
    for (const r of rows) {
      const arr = map.get(r.meta.group) ?? [];
      arr.push(r);
      map.set(r.meta.group, arr);
    }
    return map;
  }, [rows]);

  const rank = state.data ? rankForLevel(state.data.level) : null;

  return (
    <AppShell>
      <main className="flex-1">
        <div className="max-w-6xl w-full mx-auto px-6 pt-8 pb-12">
          <header className="mb-6">
            <h1 className="text-[28px] font-bold tracking-tight text-[var(--color-text)]">
              Achievements
            </h1>
            <p className="text-[14px] text-[var(--color-text-3)] mt-1">
              Earn badges by showing up. Every action counts.
            </p>
          </header>

          {state.data ? (
            <HeroBar
              level={state.data.level}
              rankTitle={rank?.title ?? "Bronze Rookie"}
              streak={state.data.streak}
              unlocked={unlockedCount}
              total={total}
              pct={overallPct}
              mostRecent={mostRecent}
            />
          ) : null}

          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-8">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="h-28 rounded-2xl bg-[var(--color-surface-2)] animate-pulse"
                />
              ))}
            </div>
          ) : (
            <div className="space-y-8 mt-8">
              {GROUP_ORDER.map((g) => {
                const items = grouped.get(g);
                if (!items || items.length === 0) return null;
                const groupUnlocked = items.filter((r) => r.unlocked_at).length;
                const groupPct = Math.round(
                  (groupUnlocked / items.length) * 100,
                );
                return (
                  <section key={g}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span
                          aria-hidden
                          className={`w-1 h-5 rounded-full bg-gradient-to-b ${GROUP_ACCENT[g]}`}
                        />
                        <h2 className="text-[13px] font-bold uppercase tracking-wide text-[var(--color-text-2)]">
                          {GROUP_LABEL[g]}
                        </h2>
                        <span className="text-[12px] text-[var(--color-text-3)] tabular-nums">
                          {groupUnlocked}/{items.length}
                        </span>
                      </div>
                      <div className="w-28 h-1.5 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
                        <div
                          className={`h-full bg-gradient-to-r ${GROUP_ACCENT[g]} transition-[width] duration-500`}
                          style={{ width: `${groupPct}%` }}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {items.map((r) => (
                        <AchievementCard key={r.meta.code} row={r} />
                      ))}
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}

function HeroBar({
  level,
  rankTitle,
  streak,
  unlocked,
  total,
  pct,
  mostRecent,
}: {
  level: number;
  rankTitle: string;
  streak: number;
  unlocked: number;
  total: number;
  pct: number;
  mostRecent: Row | undefined;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl ring-1 ring-[var(--color-border)] bg-gradient-to-br from-indigo-500/10 via-[var(--color-surface)] to-fuchsia-500/10 p-5 shadow-sm">
      <div
        aria-hidden
        className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-gradient-to-br from-indigo-300 to-fuchsia-300 opacity-20 blur-2xl"
      />
      <div className="relative flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="relative grid place-items-center w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-white text-[22px] font-black shadow-lg ring-4 ring-[var(--color-surface)]">
            {level}
            {level >= 5 ? (
              <Crown
                aria-hidden
                className="absolute -top-2 w-4 h-4 text-yellow-300 drop-shadow"
              />
            ) : null}
          </div>
          <div>
            <div className="text-[12px] uppercase tracking-widest text-[var(--color-text-3)] font-semibold">
              Rank
            </div>
            <div className="text-[18px] font-bold text-[var(--color-text)]">
              {rankTitle}
            </div>
          </div>
        </div>

        <div className="h-10 w-px bg-[var(--color-border)] hidden sm:block" />

        <div>
          <div className="text-[12px] uppercase tracking-widest text-[var(--color-text-3)] font-semibold">
            Streak
          </div>
          <div className="text-[18px] font-bold text-[var(--color-text)] tabular-nums">
            {streak} day{streak === 1 ? "" : "s"}
          </div>
        </div>

        <div className="h-10 w-px bg-[var(--color-border)] hidden sm:block" />

        <div className="flex-1 min-w-[200px]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[12px] uppercase tracking-widest text-[var(--color-text-3)] font-semibold">
              Achievements
            </span>
            <span className="text-[12px] tabular-nums text-[var(--color-text-2)] font-semibold">
              {unlocked}/{total} · {pct}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 transition-[width] duration-700"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {mostRecent ? (
          <div className="flex items-center gap-2.5 rounded-xl bg-[var(--color-surface)]/80 backdrop-blur ring-1 ring-[var(--color-border)] px-3 py-2 shadow-sm">
            <Trophy
              aria-hidden
              className={`w-4 h-4 ${TIER_CLASSES[mostRecent.meta.tier].text}`}
            />
            <div className="min-w-0">
              <div className="text-[10.5px] uppercase tracking-widest text-[var(--color-text-3)] font-semibold">
                Latest unlock
              </div>
              <div className="text-[13px] font-semibold text-[var(--color-text)] truncate max-w-[180px]">
                {mostRecent.meta.title}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function AchievementCard({ row }: { row: Row }) {
  const { meta, unlocked_at } = row;
  const Icon = meta.icon;
  const tier = TIER_CLASSES[meta.tier];
  const unlocked = Boolean(unlocked_at);
  const cardRef = useRef<HTMLDivElement>(null);

  function handleMove(e: MouseEvent<HTMLDivElement>) {
    if (!unlocked) return;
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / rect.width;
    const dy = (e.clientY - cy) / rect.height;
    el.style.setProperty("--tilt-x", `${(-dy * 8).toFixed(2)}deg`);
    el.style.setProperty("--tilt-y", `${(dx * 8).toFixed(2)}deg`);
    el.style.transform = `perspective(800px) rotateX(${-dy * 8}deg) rotateY(${dx * 8}deg)`;
  }
  function handleLeave() {
    const el = cardRef.current;
    if (!el) return;
    el.style.transform = "perspective(800px) rotateX(0deg) rotateY(0deg)";
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      className={`group relative rounded-2xl bg-[var(--color-surface)] ring-1 p-4 transition-all duration-200 ease-out will-change-transform ${
        unlocked
          ? `${tier.ring} hover:${tier.glow.replace("shadow", "shadow")} hover:shadow-lg`
          : "ring-[var(--color-border)] opacity-75"
      }`}
      style={{ transformStyle: "preserve-3d" }}
    >
      {unlocked ? (
        <span
          aria-hidden
          className={`pointer-events-none absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity blur-md ${tier.bg}`}
        />
      ) : null}
      <div className="relative flex items-start gap-3">
        <div
          className={`grid place-items-center w-11 h-11 rounded-xl shrink-0 ${
            unlocked
              ? `${tier.bg} ${tier.text}`
              : "bg-[var(--color-surface-2)] text-[var(--color-text-3)]"
          }`}
        >
          {unlocked ? (
            <>
              <Icon className="w-5 h-5" />
              <Sparkles
                aria-hidden
                className="absolute -top-1 -right-1 w-3 h-3 text-yellow-400 opacity-0 group-hover:opacity-100 sparkle-twinkle"
              />
            </>
          ) : (
            <Lock className="w-4 h-4" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[14px] font-bold text-[var(--color-text)] truncate">
              {meta.title}
            </span>
            <span
              className={`shrink-0 px-1.5 rounded-full text-[9.5px] font-bold tracking-wider ${tier.bg} ${tier.text}`}
            >
              {meta.tier.toUpperCase()}
            </span>
          </div>
          <p className="text-[12px] text-[var(--color-text-3)] leading-snug mt-0.5">
            {meta.description}
          </p>
          {unlocked && unlocked_at ? (
            <p className="text-[11px] text-[var(--color-text-3)] mt-1.5">
              Unlocked{" "}
              {formatDistanceToNowStrict(parseISO(unlocked_at), {
                addSuffix: true,
              })}
            </p>
          ) : (
            <p className="text-[11px] text-[var(--color-text-3)] mt-1.5">Locked</p>
          )}
        </div>
      </div>
    </div>
  );
}

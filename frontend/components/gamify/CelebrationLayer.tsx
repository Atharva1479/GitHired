"use client";

import confetti from "canvas-confetti";
import { Medal, Sparkles, X, Zap } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  useGamifyAcknowledge,
  useGamifyListener,
  useGamifyState,
} from "@/hooks/useGamify";
import {
  type AchievementTier,
  TIER_CLASSES,
  metaFor,
} from "@/lib/achievements";
import type { GamifyEnvelope } from "@/lib/api";
import { haptic, sfx } from "@/lib/sfx";

import { LevelUpTakeover } from "./LevelUpTakeover";

type ToastItem = {
  id: number;
  code: string;
};

const TIER_FOR_TIER: Record<AchievementTier, AchievementTier> = {
  bronze: "bronze",
  silver: "silver",
  gold: "gold",
  platinum: "platinum",
};

export function CelebrationLayer() {
  const [levelUp, setLevelUp] = useState<{
    next: number;
    previous: number;
  } | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [dailyGoalBurst, setDailyGoalBurst] = useState(false);
  const [comboTier, setComboTier] = useState<number | null>(null);

  const idRef = useRef(1);
  const acknowledge = useGamifyAcknowledge();
  const { data: state } = useGamifyState();
  const shownUnseenRef = useRef<number | null>(null);
  const prevLevelRef = useRef<number | null>(null);
  const prevDailyDoneRef = useRef<number | null>(null);
  const dailyBurstFiredRef = useRef<string | null>(null);
  const comboBucketRef = useRef<number[]>([]);

  const enqueueToast = useCallback((code: string) => {
    const id = idRef.current++;
    setToasts((t) => [...t, { id, code }].slice(-3));
    window.setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 5400);
  }, []);

  const closeLevelUp = useCallback(() => {
    setLevelUp(null);
    acknowledge.mutate();
  }, [acknowledge]);

  // ── Listen for real-time envelopes ──────────────────────────────
  useGamifyListener((env: GamifyEnvelope) => {
    sfx.unlock();

    // Sound + haptic for XP gains.
    if (env.xp_gained > 0) {
      sfx.xp();
      // combo detection: count xp gains in last 60s
      const now = Date.now();
      comboBucketRef.current = [
        ...comboBucketRef.current.filter((t) => now - t < 60_000),
        now,
      ];
      const count = comboBucketRef.current.length;
      if (count >= 3) {
        setComboTier(count);
        sfx.combo();
        haptic(8);
        window.setTimeout(() => setComboTier(null), 1500);
      }
    }

    // Quest completion sound (separate from achievement unlock).
    if (env.quest_completed.length > 0 && env.unlocked.length === 0) {
      sfx.questDone();
      haptic([10, 20, 10]);
      smallConfetti();
    }

    // Achievement unlocks — toasts, tiered sound, sparkle burst.
    if (env.unlocked.length > 0) {
      env.unlocked.forEach((code, i) => {
        window.setTimeout(() => {
          enqueueToast(code);
          const meta = metaFor(code);
          sfx.achievement(TIER_FOR_TIER[meta.tier]);
        }, i * 280);
      });
      haptic([15, 25, 15, 25]);
      sideConfetti();
    }
  });

  // ── Detect level-up via envelope OR persisted unseen flag ───────
  useEffect(() => {
    if (!state) return;
    const prev = prevLevelRef.current;
    prevLevelRef.current = state.level;

    if (state.unseen_level_up && shownUnseenRef.current !== state.unseen_level_up) {
      shownUnseenRef.current = state.unseen_level_up;
      setLevelUp({
        next: state.unseen_level_up,
        previous: prev ?? state.level - 1,
      });
    }
  }, [state]);

  // ── Detect daily-goal-complete transition ───────────────────────
  useEffect(() => {
    if (!state) return;
    const dailies = state.daily_quests;
    if (dailies.length === 0) return;
    const done = dailies.filter((q) => q.completed).length;
    const prev = prevDailyDoneRef.current;
    prevDailyDoneRef.current = done;

    const today = new Date().toISOString().slice(0, 10);
    const lastFired = dailyBurstFiredRef.current;
    if (lastFired === today) return;

    if (
      done === dailies.length &&
      prev !== null &&
      prev < dailies.length
    ) {
      dailyBurstFiredRef.current = today;
      setDailyGoalBurst(true);
      sfx.dailyGoal();
      haptic([20, 30, 20, 30, 40]);
      bigConfetti();
      window.setTimeout(() => setDailyGoalBurst(false), 2400);
    }
  }, [state]);

  return (
    <>
      {levelUp ? (
        <LevelUpTakeover
          level={levelUp.next}
          previousLevel={levelUp.previous}
          onClose={closeLevelUp}
        />
      ) : null}

      {dailyGoalBurst ? <DailyGoalBurst /> : null}
      {comboTier ? <ComboBubble count={comboTier} /> : null}

      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <UnlockToast
            key={t.id}
            code={t.code}
            onDismiss={() =>
              setToasts((q) => q.filter((x) => x.id !== t.id))
            }
          />
        ))}
      </div>
    </>
  );
}

function UnlockToast({
  code,
  onDismiss,
}: {
  code: string;
  onDismiss: () => void;
}) {
  const meta = metaFor(code);
  const Icon = meta.icon;
  const tier = TIER_CLASSES[meta.tier];
  return (
    <div
      role="status"
      className={`spring-in pointer-events-auto relative flex items-start gap-3 w-80 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] ${tier.glow} px-3.5 py-3`}
    >
      <div
        aria-hidden
        className={`absolute -inset-0.5 rounded-2xl ${tier.bg} opacity-40 blur-md aura-breathe`}
      />
      <div
        className={`relative grid place-items-center w-11 h-11 rounded-xl ${tier.bg} ${tier.text} shrink-0 badge-spin-in shadow-inner`}
      >
        <Icon className="w-5 h-5" />
        <Sparkles
          aria-hidden
          className="absolute -top-2 -right-1 w-3.5 h-3.5 text-yellow-400 sparkle-twinkle"
        />
      </div>
      <div className="relative flex-1 min-w-0">
        <div className="flex items-center gap-1.5 text-[10.5px] uppercase tracking-wider text-[var(--color-text-3)] font-semibold">
          <Zap className="w-3 h-3 text-indigo-500" />
          <span>Achievement unlocked</span>
          <TierPill tier={meta.tier} />
        </div>
        <div className="text-[14px] font-bold text-[var(--color-text)] truncate mt-0.5">
          {meta.title}
        </div>
        <div className="text-[12px] text-[var(--color-text-3)] leading-snug">
          {meta.description}
        </div>
      </div>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="relative shrink-0 text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function TierPill({ tier }: { tier: AchievementTier }) {
  const cls = TIER_CLASSES[tier];
  return (
    <span
      className={`px-1.5 rounded-full text-[9.5px] font-bold tracking-wider ${cls.bg} ${cls.text}`}
    >
      {tier.toUpperCase()}
    </span>
  );
}

function DailyGoalBurst() {
  return (
    <div
      role="status"
      aria-label="Daily goal complete"
      className="fade-up fixed left-1/2 top-24 -translate-x-1/2 z-[55] pointer-events-none"
    >
      <div className="relative flex items-center gap-2.5 rounded-full bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white px-5 py-2.5 shadow-2xl ring-2 ring-white/30">
        <span
          aria-hidden
          className="absolute inset-0 rounded-full aura-breathe bg-emerald-400/40 blur-md"
        />
        <Medal className="relative w-5 h-5 drop-shadow" />
        <span className="relative font-bold text-[15px] tracking-tight">
          Daily goal complete!
        </span>
        <span className="relative text-[11px] uppercase tracking-widest text-white/85 font-semibold">
          +bonus XP
        </span>
      </div>
    </div>
  );
}

function ComboBubble({ count }: { count: number }) {
  return (
    <div
      aria-hidden
      className="combo-pop fixed right-8 top-20 z-[55] pointer-events-none"
    >
      <div className="rounded-full bg-gradient-to-r from-fuchsia-500 to-orange-500 text-white font-black px-4 py-1.5 text-[13px] tracking-wider uppercase shadow-2xl ring-2 ring-white/30">
        Combo ×{count}!
      </div>
    </div>
  );
}

// ── Confetti recipes ───────────────────────────────────────────────

function sideConfetti() {
  confetti({
    particleCount: 60,
    spread: 75,
    origin: { x: 0.9, y: 0.95 },
    colors: ["#6366f1", "#8b5cf6", "#f59e0b", "#ec4899"],
    scalar: 1.05,
  });
}

function smallConfetti() {
  confetti({
    particleCount: 28,
    spread: 55,
    startVelocity: 28,
    origin: { x: 0.5, y: 0.92 },
    colors: ["#10b981", "#6366f1", "#f59e0b"],
  });
}

function bigConfetti() {
  const colors = ["#10b981", "#0ea5e9", "#f59e0b", "#ec4899", "#8b5cf6"];
  const end = Date.now() + 1600;
  const tick = () => {
    confetti({
      particleCount: 5,
      angle: 60,
      spread: 65,
      origin: { x: 0, y: 0.6 },
      colors,
    });
    confetti({
      particleCount: 5,
      angle: 120,
      spread: 65,
      origin: { x: 1, y: 0.6 },
      colors,
    });
    if (Date.now() < end) requestAnimationFrame(tick);
  };
  tick();
  confetti({
    particleCount: 80,
    spread: 90,
    origin: { x: 0.5, y: 0.35 },
    colors,
    scalar: 1.1,
    startVelocity: 38,
  });
}

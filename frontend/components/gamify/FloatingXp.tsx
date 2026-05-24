"use client";

import { useEffect, useRef, useState } from "react";

import type { GamifyEnvelope } from "@/lib/api";

type Particle = {
  id: number;
  amount: number;
  startX: number;
  startY: number;
  midX: number;
  endX: number;
  endY: number;
};

const STACK_WINDOW_MS = 900;

/**
 * Floating "+N XP" particles that arc from the action site up to the
 * XP bar in the TopBar. Stacks rapid bursts to avoid spamming the screen.
 */
export function FloatingXp() {
  const [particles, setParticles] = useState<Particle[]>([]);
  const idRef = useRef(1);
  const lastClickRef = useRef<{ x: number; y: number } | null>(null);
  const lastSpawnRef = useRef<number>(0);

  // Track the most recent user gesture so the bubble emerges near it.
  useEffect(() => {
    const onPointer = (e: PointerEvent) => {
      lastClickRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("pointerdown", onPointer);
    return () => window.removeEventListener("pointerdown", onPointer);
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const env = (e as CustomEvent<GamifyEnvelope>).detail;
      if (!env || env.duplicate || env.xp_gained <= 0) return;

      const target = document.querySelector<HTMLElement>(
        "[data-xp-target='1']",
      );
      if (!target) return;
      const tRect = target.getBoundingClientRect();
      const endXAbs = tRect.left + tRect.width / 2;
      const endYAbs = tRect.top + tRect.height / 2;

      const click = lastClickRef.current;
      const src = click ?? {
        x: window.innerWidth / 2,
        y: window.innerHeight - 120,
      };

      const now = Date.now();
      const stacking = now - lastSpawnRef.current < STACK_WINDOW_MS;
      lastSpawnRef.current = now;

      if (stacking) {
        // Merge into the newest particle.
        setParticles((prev) => {
          if (prev.length === 0) return prev;
          const next = [...prev];
          const last = next[next.length - 1];
          next[next.length - 1] = {
            ...last,
            amount: last.amount + env.xp_gained,
          };
          return next;
        });
        return;
      }

      const id = idRef.current++;
      const midX = (endXAbs - src.x) * 0.35;
      const p: Particle = {
        id,
        amount: env.xp_gained,
        startX: src.x,
        startY: src.y,
        midX,
        endX: endXAbs - src.x,
        endY: endYAbs - src.y,
      };
      setParticles((prev) => [...prev, p]);
      window.setTimeout(() => {
        setParticles((prev) => prev.filter((x) => x.id !== id));
      }, 1200);
    };
    window.addEventListener("jp:gamify", handler);
    return () => window.removeEventListener("jp:gamify", handler);
  }, []);

  if (particles.length === 0) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[60]">
      {particles.map((p) => (
        <span
          key={p.id}
          className="xp-fly absolute flex items-center gap-1 rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 px-2.5 py-0.5 text-[12px] font-bold text-white shadow-[0_6px_18px_rgba(99,102,241,0.6)] ring-1 ring-white/40"
          style={
            {
              left: `${p.startX}px`,
              top: `${p.startY}px`,
              transform: "translate(-50%, -50%)",
              "--xp-mid-x": `${p.midX}px`,
              "--xp-end-x": `${p.endX}px`,
              "--xp-end-y": `${p.endY}px`,
            } as React.CSSProperties
          }
        >
          +{p.amount} XP
        </span>
      ))}
    </div>
  );
}

"use client";

import type { AgentStatus } from "@/hooks/useVoiceAgent";

type Palette = {
  a: string;
  b: string;
  c: string;
  d: string;
  e: string;
  rim: string;
  outerGlow: string;
};

const PALETTES: Record<AgentStatus, Palette> = {
  idle: {
    a: "rgba(129, 140, 248, 0.92)", // indigo-400
    b: "rgba(192, 132, 252, 0.88)", // fuchsia-300
    c: "rgba(56, 189, 248, 0.78)",  // sky-400
    d: "rgba(244, 114, 182, 0.62)", // pink-400
    e: "rgba(255, 255, 255, 0.55)",
    rim: "rgba(199, 210, 254, 0.55)",
    outerGlow: "rgba(99, 102, 241, 0.45)",
  },
  recording: {
    a: "rgba(244, 114, 182, 0.95)",
    b: "rgba(251, 113, 133, 0.92)",
    c: "rgba(252, 165, 165, 0.80)",
    d: "rgba(253, 224, 71, 0.45)",
    e: "rgba(255, 255, 255, 0.55)",
    rim: "rgba(253, 164, 175, 0.7)",
    outerGlow: "rgba(244, 63, 94, 0.55)",
  },
  transcribing: {
    a: "rgba(56, 189, 248, 0.95)",
    b: "rgba(129, 140, 248, 0.9)",
    c: "rgba(147, 197, 253, 0.8)",
    d: "rgba(165, 243, 252, 0.55)",
    e: "rgba(255, 255, 255, 0.55)",
    rim: "rgba(191, 219, 254, 0.6)",
    outerGlow: "rgba(56, 189, 248, 0.5)",
  },
  thinking: {
    a: "rgba(167, 139, 250, 0.95)",
    b: "rgba(96, 165, 250, 0.85)",
    c: "rgba(216, 180, 254, 0.82)",
    d: "rgba(129, 140, 248, 0.6)",
    e: "rgba(255, 255, 255, 0.55)",
    rim: "rgba(221, 214, 254, 0.6)",
    outerGlow: "rgba(139, 92, 246, 0.55)",
  },
  speaking: {
    a: "rgba(232, 121, 249, 0.95)", // fuchsia-400
    b: "rgba(244, 114, 182, 0.92)", // pink-400
    c: "rgba(192, 132, 252, 0.88)", // fuchsia-300
    d: "rgba(167, 139, 250, 0.7)",
    e: "rgba(255, 255, 255, 0.7)",
    rim: "rgba(245, 208, 254, 0.75)",
    outerGlow: "rgba(217, 70, 239, 0.6)",
  },
};

export type AuroraOrbProps = {
  status: AgentStatus;
  /** 0..1 — driven by live AnalyserNode amplitude */
  amplitude: number;
  /** Pixel size of the orb (square). */
  size?: number;
};

/**
 * AuroraOrb — an ethereal cloud of colored light, not a ball.
 *
 * Five heavily-blurred radial-gradient blobs orbit slowly inside a
 * circular glass viewport. Their colours blend into an aurora-like haze
 * that breathes with `amplitude`. A subtle chromatic rim, an inner
 * top-left sheen, and a soft outer glow give it a sense of depth without
 * looking like a sphere.
 *
 * All CSS — no canvas, no WebGL. Crisp at any size, cheap to animate.
 */
export function AuroraOrb({ status, amplitude, size = 200 }: AuroraOrbProps) {
  const p = PALETTES[status] ?? PALETTES.idle;
  const a = Math.max(0, Math.min(1, amplitude));
  // Container scales slightly with amplitude; blobs brighten via opacity.
  const scale = 1 + a * 0.05;
  const brightness = 1 + a * 0.35;
  const blur = 26 + a * 6; // px — looser when louder for halo feel

  return (
    <div
      className="relative pointer-events-none select-none"
      style={{ width: size, height: size }}
    >
      {/* Outer halo glow */}
      <div
        aria-hidden
        className="absolute inset-[-22%] rounded-full"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${p.outerGlow} 0%, transparent 65%)`,
          filter: `blur(${24 + a * 10}px)`,
          opacity: 0.55 + a * 0.35,
          transform: `scale(${1 + a * 0.08})`,
          transition: "opacity 240ms ease-out, transform 240ms ease-out",
        }}
      />

      {/* Chromatic rim — two thin counter-rotating arcs */}
      <div
        aria-hidden
        className="absolute inset-0 rounded-full rim-spin"
        style={{
          background: `conic-gradient(from 0deg, ${p.rim} 0deg, transparent 80deg, ${p.rim} 180deg, transparent 260deg, ${p.rim} 360deg)`,
          padding: "1px",
          WebkitMask:
            "radial-gradient(circle, transparent 49%, black 50%, black 51%, transparent 52%)",
          mask: "radial-gradient(circle, transparent 49%, black 50%, black 51%, transparent 52%)",
          opacity: 0.65,
        }}
      />
      <div
        aria-hidden
        className="absolute inset-0 rounded-full rim-spin-rev"
        style={{
          background: `conic-gradient(from 90deg, transparent 0deg, ${p.rim} 60deg, transparent 140deg, ${p.rim} 220deg, transparent 300deg)`,
          padding: "1px",
          WebkitMask:
            "radial-gradient(circle, transparent 47%, black 48%, black 49%, transparent 50%)",
          mask: "radial-gradient(circle, transparent 47%, black 48%, black 49%, transparent 50%)",
          opacity: 0.45,
        }}
      />

      {/* Glass viewport that contains the aurora cloud */}
      <div
        className="absolute inset-[6%] rounded-full overflow-hidden"
        style={{
          transform: `scale(${scale})`,
          transition: "transform 120ms ease-out",
          boxShadow:
            "inset 0 0 30px rgba(255,255,255,0.05), inset 0 0 60px rgba(15,23,42,0.6)",
          background:
            "radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%)",
        }}
      >
        <div
          className="absolute inset-0"
          style={{ filter: `blur(${blur}px) saturate(140%) brightness(${brightness})` }}
        >
          <Blob className="blob-a" color={p.a} top="-10%" left="-10%" size={130} />
          <Blob className="blob-b" color={p.b} top="40%" left="40%" size={120} />
          <Blob className="blob-c" color={p.c} top="55%" left="-10%" size={100} />
          <Blob className="blob-d" color={p.d} top="-15%" left="50%" size={95} />
          <Blob className="blob-e" color={p.e} top="20%" left="20%" size={60} />
        </div>

        {/* Top-left sheen — gives the orb a "glass" feel without making it a ball */}
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 60% 35% at 32% 25%, rgba(255,255,255,0.28) 0%, transparent 60%)",
            mixBlendMode: "screen",
          }}
        />

        {/* Soft inner ring — like the edge of frosted glass */}
        <div
          aria-hidden
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            boxShadow:
              "inset 0 0 0 1px rgba(255,255,255,0.08), inset 0 0 24px rgba(255,255,255,0.04)",
          }}
        />
      </div>
    </div>
  );
}

function Blob({
  className,
  color,
  top,
  left,
  size,
}: {
  className: string;
  color: string;
  top: string;
  left: string;
  size: number;
}) {
  return (
    <span
      aria-hidden
      className={`absolute rounded-full ${className}`}
      style={{
        top,
        left,
        width: `${size}%`,
        height: `${size}%`,
        background: `radial-gradient(circle at 50% 50%, ${color} 0%, transparent 70%)`,
        willChange: "transform",
      }}
    />
  );
}

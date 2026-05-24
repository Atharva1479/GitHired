"use client";

import { useMemo } from "react";

import type { AgentStatus } from "@/hooks/useVoiceAgent";

type Palette = {
  coreOuter: string;
  coreInner: string;
  rim: string;
  particles: string;
  glow: string;
};

const PALETTES: Record<AgentStatus, Palette> = {
  idle: {
    coreOuter: "#312e81",
    coreInner: "#a5b4fc",
    rim: "rgba(165, 180, 252, 0.5)",
    particles: "#c7d2fe",
    glow: "rgba(99, 102, 241, 0.45)",
  },
  recording: {
    coreOuter: "#9d174d",
    coreInner: "#fda4af",
    rim: "rgba(253, 164, 175, 0.75)",
    particles: "#fecdd3",
    glow: "rgba(244, 63, 94, 0.55)",
  },
  transcribing: {
    coreOuter: "#1e3a8a",
    coreInner: "#93c5fd",
    rim: "rgba(147, 197, 253, 0.65)",
    particles: "#bfdbfe",
    glow: "rgba(59, 130, 246, 0.5)",
  },
  thinking: {
    coreOuter: "#3730a3",
    coreInner: "#c4b5fd",
    rim: "rgba(196, 181, 253, 0.7)",
    particles: "#ddd6fe",
    glow: "rgba(139, 92, 246, 0.55)",
  },
  speaking: {
    coreOuter: "#5b21b6",
    coreInner: "#e9d5ff",
    rim: "rgba(233, 213, 255, 0.85)",
    particles: "#f5d0fe",
    glow: "rgba(168, 85, 247, 0.6)",
  },
};

export type JarvisOrbProps = {
  status: AgentStatus;
  /** 0..1 — driven by live AnalyserNode amplitude */
  amplitude: number;
  /** Pixel size of the SVG viewport (square). */
  size?: number;
};

/**
 * Centerpiece of voice mode. SVG-based for crisp scaling and zero
 * canvas/WebGL overhead. The orb breathes on its own (CSS keyframes) and
 * additionally swells with live `amplitude`, so it ripples to whatever
 * audio is active — mic input while listening, TTS playback while
 * speaking.
 */
export function JarvisOrb({ status, amplitude, size = 320 }: JarvisOrbProps) {
  const palette = PALETTES[status] ?? PALETTES.idle;

  // amplitude (0..1) drives a gentle radius expansion. Clamp + curve so
  // the orb feels responsive but never thrashes.
  const a = Math.max(0, Math.min(1, amplitude));
  const swell = a * a * 0.5 + a * 0.4; // 0..0.9
  const rCore = 78 + swell * 28;
  const rHalo = 110 + swell * 24;
  const rOuterRing = 138 + swell * 12;
  const rimOpacity = 0.35 + a * 0.55;

  // Particle ring — fixed positions in viewBox space, animated via CSS
  // rotation on parent <g>. Generated once per palette.
  const particles = useMemo(() => {
    const ring1 = 12;
    const ring2 = 8;
    const out: { cx: number; cy: number; r: number; opacity: number }[] = [];
    for (let i = 0; i < ring1; i++) {
      const t = (i / ring1) * Math.PI * 2;
      out.push({
        cx: Math.cos(t) * 158,
        cy: Math.sin(t) * 158,
        r: 1.8 + (i % 3) * 0.4,
        opacity: 0.55 + (i % 4) * 0.1,
      });
    }
    for (let i = 0; i < ring2; i++) {
      const t = (i / ring2) * Math.PI * 2 + Math.PI / 8;
      out.push({
        cx: Math.cos(t) * 178,
        cy: Math.sin(t) * 178,
        r: 1.2 + (i % 2) * 0.5,
        opacity: 0.35 + (i % 3) * 0.1,
      });
    }
    return out;
  }, []);

  return (
    <div
      className="relative grid place-items-center pointer-events-none"
      style={{ width: size, height: size }}
    >
      {/* Soft outer glow — pure CSS, sits behind the SVG. */}
      <div
        aria-hidden
        className="absolute inset-0 rounded-full orb-aura"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${palette.glow} 0%, transparent 65%)`,
          filter: "blur(18px)",
          transform: `scale(${1 + a * 0.18})`,
        }}
      />

      <svg
        viewBox="-200 -200 400 400"
        width={size}
        height={size}
        className="relative"
        aria-hidden
      >
        <defs>
          <radialGradient id="orb-core" cx="40%" cy="38%" r="65%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="35%" stopColor={palette.coreInner} stopOpacity="0.95" />
            <stop offset="85%" stopColor={palette.coreOuter} stopOpacity="1" />
            <stop offset="100%" stopColor="#0b0f1f" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="orb-halo" cx="50%" cy="50%" r="50%">
            <stop offset="60%" stopColor={palette.coreInner} stopOpacity="0" />
            <stop offset="95%" stopColor={palette.coreInner} stopOpacity="0.18" />
            <stop offset="100%" stopColor={palette.coreInner} stopOpacity="0" />
          </radialGradient>
          <filter id="soft-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="1.3" />
            </feComponentTransfer>
          </filter>
        </defs>

        {/* Outer faint ring — slowest motion */}
        <g className="orb-rotate-slow">
          <circle
            r={rOuterRing}
            fill="none"
            stroke={palette.rim}
            strokeOpacity={rimOpacity * 0.45}
            strokeWidth={0.6}
            strokeDasharray="2 6"
          />
        </g>

        {/* Particle rings — orbiting in opposite directions */}
        <g className="orb-rotate-slow">
          {particles.slice(0, 12).map((p, i) => (
            <circle
              key={`p1-${i}`}
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              fill={palette.particles}
              opacity={p.opacity}
              filter="url(#soft-glow)"
            />
          ))}
        </g>
        <g className="orb-rotate-fast">
          {particles.slice(12).map((p, i) => (
            <circle
              key={`p2-${i}`}
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              fill={palette.particles}
              opacity={p.opacity}
              filter="url(#soft-glow)"
            />
          ))}
        </g>

        {/* Inner halo (between core and rim) */}
        <circle r={rHalo} fill="url(#orb-halo)" />

        {/* Live rim that swells with amplitude */}
        <circle
          r={rCore + 16}
          fill="none"
          stroke={palette.rim}
          strokeOpacity={rimOpacity}
          strokeWidth={1.2}
        />
        <circle
          r={rCore + 8}
          fill="none"
          stroke={palette.rim}
          strokeOpacity={rimOpacity * 0.55}
          strokeWidth={0.8}
        />

        {/* Core */}
        <g className="orb-breathe">
          <circle r={rCore} fill="url(#orb-core)" />
          {/* Subtle highlight to give it a 3D feel */}
          <ellipse
            cx={-22}
            cy={-32}
            rx={28}
            ry={18}
            fill="white"
            opacity="0.18"
            transform="rotate(-22)"
          />
        </g>
      </svg>
    </div>
  );
}

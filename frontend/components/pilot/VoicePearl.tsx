"use client";

import { useEffect, useRef } from "react";

import type { AgentStatus } from "@/hooks/useVoiceAgent";

type Palette = {
  /** Stops of the main fill gradient. */
  c1: string;
  c2: string;
  c3: string;
  /** Inner highlight gradient stop. */
  inner: string;
  /** Outer soft glow. */
  glow: string;
  /** Color of the listening ripple rings. */
  ripple: string;
};

const PALETTES: Record<AgentStatus, Palette> = {
  idle: {
    c1: "#a78bfa",
    c2: "#f0abfc",
    c3: "#22d3ee",
    inner: "rgba(255, 255, 255, 0.55)",
    glow: "rgba(167, 139, 250, 0.55)",
    ripple: "rgba(199, 210, 254, 0.45)",
  },
  recording: {
    c1: "#fb7185",
    c2: "#fbbf24",
    c3: "#f472b6",
    inner: "rgba(255, 255, 255, 0.6)",
    glow: "rgba(244, 63, 94, 0.55)",
    ripple: "rgba(253, 164, 175, 0.65)",
  },
  transcribing: {
    c1: "#38bdf8",
    c2: "#a78bfa",
    c3: "#22d3ee",
    inner: "rgba(255, 255, 255, 0.55)",
    glow: "rgba(56, 189, 248, 0.5)",
    ripple: "rgba(165, 243, 252, 0.5)",
  },
  thinking: {
    c1: "#a78bfa",
    c2: "#c084fc",
    c3: "#60a5fa",
    inner: "rgba(255, 255, 255, 0.55)",
    glow: "rgba(139, 92, 246, 0.55)",
    ripple: "rgba(221, 214, 254, 0.5)",
  },
  speaking: {
    c1: "#e879f9",
    c2: "#f472b6",
    c3: "#facc15",
    inner: "rgba(255, 255, 255, 0.7)",
    glow: "rgba(217, 70, 239, 0.6)",
    ripple: "rgba(245, 208, 254, 0.55)",
  },
};

const VIEW = 130; // SVG viewBox half-size × 2 (centered at 0,0; box is [-65, -65, 130, 130])
const BASE_R = 50; // resting radius of the blob
const N = 9; // control points around the blob

/**
 * Build a smooth, closed bezier path through N points laid out around a
 * circle of radius R. Each point's radius wobbles with its own sine wave
 * so the shape morphs organically over time. Amplitude (audio) adds an
 * extra outward push so the blob "breathes" with sound.
 *
 * Uses Catmull-Rom → cubic-bezier conversion for C1-continuous curves.
 */
function buildBlobPath(t: number, amp: number, baseR = BASE_R, wobble = 0.16): string {
  const points: [number, number][] = [];
  for (let i = 0; i < N; i++) {
    const angle = (i / N) * Math.PI * 2;
    const freq = 0.45 + (i % 3) * 0.13;
    const phase = i * 0.81;
    const r =
      baseR * (1 + wobble * Math.sin(t * freq + phase)) +
      amp * 16 * Math.sin(t * 1.4 + i * 0.6);
    points.push([Math.cos(angle) * r, Math.sin(angle) * r]);
  }
  const k = 1 / 6; // Catmull-Rom tension
  let d = `M${points[0][0].toFixed(2)},${points[0][1].toFixed(2)}`;
  for (let i = 0; i < N; i++) {
    const p0 = points[(i - 1 + N) % N];
    const p1 = points[i];
    const p2 = points[(i + 1) % N];
    const p3 = points[(i + 2) % N];
    const c1x = p1[0] + (p2[0] - p0[0]) * k;
    const c1y = p1[1] + (p2[1] - p0[1]) * k;
    const c2x = p2[0] - (p3[0] - p1[0]) * k;
    const c2y = p2[1] - (p3[1] - p1[1]) * k;
    d +=
      ` C${c1x.toFixed(2)},${c1y.toFixed(2)} ` +
      `${c2x.toFixed(2)},${c2y.toFixed(2)} ` +
      `${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }
  return d + "Z";
}

export type VoicePearlProps = {
  status: AgentStatus;
  /** 0..1 — live AnalyserNode amplitude */
  amplitude: number;
  /** Pixel size of the pearl (square). */
  size?: number;
  onClick?: () => void;
};

/**
 * The voice agent visual — a morphing iridescent pearl of light.
 *
 * - SVG path morphs every frame via requestAnimationFrame; no React
 *   re-renders for the animation itself (we setAttribute directly).
 * - Two layered morphing paths (slightly out of phase) give a sense of
 *   inner depth instead of looking like a flat circle.
 * - Outer halo, rotating sheen, and a specular highlight at top-left
 *   make it read as a "pearl" without being a perfect sphere.
 * - When listening, three ripple rings emanate outward to make recording
 *   state visually unmistakable.
 */
export function VoicePearl({
  status,
  amplitude,
  size = 130,
  onClick,
}: VoicePearlProps) {
  const p = PALETTES[status] ?? PALETTES.idle;
  const ampRef = useRef(amplitude);
  ampRef.current = amplitude;
  const pathRef = useRef<SVGPathElement>(null);
  const innerPathRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = () => {
      const t = (performance.now() - start) / 1000;
      const a = ampRef.current;
      if (pathRef.current) {
        pathRef.current.setAttribute("d", buildBlobPath(t, a));
      }
      if (innerPathRef.current) {
        innerPathRef.current.setAttribute(
          "d",
          buildBlobPath(t + 2.3, a * 0.6, 36, 0.22),
        );
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const recording = status === "recording";

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={
        status === "idle"
          ? "Start listening"
          : status === "recording"
            ? "Stop and send"
            : status === "speaking"
              ? "Jarvis is speaking — listening resumes when finished"
              : "Voice agent busy"
      }
      className="relative block focus:outline-none cursor-pointer transition-transform duration-200 active:scale-95 hover:scale-[1.04]"
      style={{ width: size, height: size, padding: 0, background: "transparent", border: 0 }}
    >
      {/* Soft outer halo — sits behind everything */}
      <div
        aria-hidden
        className="absolute inset-[-32%] rounded-full pointer-events-none"
        style={{
          background: `radial-gradient(circle at 50% 50%, ${p.glow} 0%, transparent 65%)`,
          filter: `blur(${22 + amplitude * 10}px)`,
          opacity: 0.65 + amplitude * 0.3,
          transition: "opacity 220ms ease-out",
        }}
      />

      {/* Ripple rings while listening — three out-of-phase pulses */}
      {recording ? (
        <>
          <span
            aria-hidden
            className="absolute inset-0 rounded-full ripple-ring"
            style={{ borderColor: p.ripple }}
          />
          <span
            aria-hidden
            className="absolute inset-0 rounded-full ripple-ring"
            style={{ borderColor: p.ripple, animationDelay: "0.6s" }}
          />
          <span
            aria-hidden
            className="absolute inset-0 rounded-full ripple-ring"
            style={{ borderColor: p.ripple, animationDelay: "1.2s" }}
          />
        </>
      ) : null}

      <svg
        viewBox={`-${VIEW / 2} -${VIEW / 2} ${VIEW} ${VIEW}`}
        width={size}
        height={size}
        className="relative"
        style={{
          filter: `drop-shadow(0 6px 20px ${p.glow})`,
          overflow: "visible",
        }}
      >
        <defs>
          <linearGradient id="pearl-fill" x1="15%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={p.c1} />
            <stop offset="55%" stopColor={p.c2} />
            <stop offset="100%" stopColor={p.c3} />
          </linearGradient>
          <radialGradient id="pearl-inner" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={p.inner} stopOpacity="0.85" />
            <stop offset="100%" stopColor={p.c2} stopOpacity="0" />
          </radialGradient>
          <radialGradient id="pearl-sheen" cx="30%" cy="22%" r="42%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
            <stop offset="60%" stopColor="#ffffff" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Main morphing blob */}
        <path ref={pathRef} fill="url(#pearl-fill)" />

        {/* Inner ghost shape — different phase, smaller — adds depth */}
        <g style={{ mixBlendMode: "screen" }}>
          <path ref={innerPathRef} fill="url(#pearl-inner)" opacity="0.7" />
        </g>

        {/* Specular highlight — gives the "pearl" feel without being a sphere */}
        <g className="orb-rotate-slow">
          <ellipse
            cx="-16"
            cy="-22"
            rx="22"
            ry="11"
            fill="url(#pearl-sheen)"
            transform="rotate(-22)"
          />
        </g>
      </svg>
    </button>
  );
}

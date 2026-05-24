"use client";

/**
 * Synthesized sound effects via the Web Audio API.
 *
 * Zero audio assets to ship — every sound is generated on the fly from
 * oscillators. Cheap, cacheable, and respectful of user volume.
 */

const STORAGE_KEY = "jp_sfx_enabled";
const MASTER_VOLUME = 0.18; // global ceiling — keep tones gentle

type Note = { freq: number; dur: number; type?: OscillatorType; delay?: number };

class SfxEngine {
  private ctx: AudioContext | null = null;
  private enabled = true;
  private listeners = new Set<(b: boolean) => void>();
  private unlocked = false;

  constructor() {
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) this.enabled = stored === "1";
  }

  /** Lazy-init the audio context. Modern browsers require a user gesture. */
  private ensureCtx(): AudioContext | null {
    if (typeof window === "undefined") return null;
    if (!this.ctx) {
      const Ctor =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      if (!Ctor) return null;
      this.ctx = new Ctor();
    }
    if (this.ctx.state === "suspended") {
      // Resume is async but fire-and-forget is fine here.
      void this.ctx.resume();
    }
    return this.ctx;
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  setEnabled(value: boolean) {
    this.enabled = value;
    try {
      localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
    } catch {}
    this.listeners.forEach((l) => l(value));
    if (value) this.ensureCtx();
  }

  subscribe(cb: (b: boolean) => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  /**
   * Call once on first user gesture so iOS/Safari unlocks audio.
   * Safe to call repeatedly — only the first invocation does work.
   */
  unlock() {
    if (this.unlocked) return;
    this.unlocked = true;
    this.ensureCtx();
  }

  // ── Public sound recipes ──────────────────────────────────────────

  xp() {
    this.play([{ freq: 880, dur: 0.08, type: "triangle" }]);
  }

  questDone() {
    this.play([
      { freq: 523.25, dur: 0.1, type: "sine" }, // C5
      { freq: 659.25, dur: 0.1, type: "sine", delay: 0.08 }, // E5
      { freq: 783.99, dur: 0.18, type: "sine", delay: 0.16 }, // G5
    ]);
  }

  dailyGoal() {
    this.play([
      { freq: 523.25, dur: 0.12, type: "triangle" },
      { freq: 659.25, dur: 0.12, type: "triangle", delay: 0.1 },
      { freq: 783.99, dur: 0.12, type: "triangle", delay: 0.2 },
      { freq: 1046.5, dur: 0.4, type: "triangle", delay: 0.3 }, // C6
    ]);
  }

  levelUp() {
    this.play([
      { freq: 392, dur: 0.1, type: "triangle" }, // G4
      { freq: 523.25, dur: 0.1, type: "triangle", delay: 0.1 }, // C5
      { freq: 659.25, dur: 0.1, type: "triangle", delay: 0.2 }, // E5
      { freq: 783.99, dur: 0.15, type: "triangle", delay: 0.3 }, // G5
      { freq: 1046.5, dur: 0.45, type: "triangle", delay: 0.45 }, // C6
    ]);
  }

  achievement(tier: "bronze" | "silver" | "gold" | "platinum") {
    const base =
      tier === "platinum"
        ? 880
        : tier === "gold"
          ? 783.99
          : tier === "silver"
            ? 659.25
            : 523.25;
    const notes: Note[] = [
      { freq: base, dur: 0.1, type: "sine" },
      { freq: base * 1.25, dur: 0.1, type: "sine", delay: 0.08 },
      { freq: base * 1.5, dur: 0.25, type: "sine", delay: 0.16 },
    ];
    if (tier === "platinum") {
      notes.push({ freq: base * 2, dur: 0.4, type: "triangle", delay: 0.3 });
    }
    this.play(notes);
  }

  streakUp() {
    this.play([
      { freq: 660, dur: 0.07, type: "square" },
      { freq: 880, dur: 0.12, type: "square", delay: 0.06 },
    ]);
  }

  combo() {
    this.play([
      { freq: 1175, dur: 0.06, type: "sawtooth" }, // D6
      { freq: 1568, dur: 0.1, type: "sawtooth", delay: 0.05 }, // G6
    ]);
  }

  // ── Engine internals ──────────────────────────────────────────────

  private play(notes: Note[]) {
    if (!this.enabled) return;
    const ctx = this.ensureCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    notes.forEach((n) => {
      const start = now + (n.delay ?? 0);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = n.type ?? "sine";
      osc.frequency.setValueAtTime(n.freq, start);
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(MASTER_VOLUME, start + 0.008);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + n.dur);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + n.dur + 0.02);
    });
  }
}

export const sfx = new SfxEngine();

/** Best-effort haptic — silently noop on desktop / unsupported browsers. */
export function haptic(pattern: number | number[] = 14) {
  if (typeof navigator === "undefined") return;
  const v = navigator.vibrate?.bind(navigator);
  if (v) v(pattern);
}

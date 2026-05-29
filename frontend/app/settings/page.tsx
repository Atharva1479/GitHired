"use client";

import { AlertCircle, Check, CheckCircle2, Loader2, Play, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { api } from "@/lib/api";
import { DEFAULT_VOICE_ID, VOICE_OPTIONS, type AiProvider } from "@/lib/settings";

const LS_CONTINUOUS = "jp_pilot_continuous_mode";
const LS_BARGE_IN   = "jp_pilot_barge_in";
const LS_FAST_TTS   = "jp_pilot_fast_browser_tts";
const LS_ORB_MODE   = "githired_interview_orb_mode";

function readLs(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v === "true";
  } catch {
    return fallback;
  }
}

function writeLs(key: string, value: boolean): void {
  try {
    localStorage.setItem(key, String(value));
  } catch {}
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function SavedToast({ visible }: { visible: boolean }) {
  return (
    <div
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-xl border border-emerald-500/20 bg-[var(--color-surface)] px-4 py-3 shadow-lg transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3 pointer-events-none"
      }`}
    >
      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
      <span className="text-[13px] font-medium text-[var(--color-text)]">Settings saved</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[11px] uppercase tracking-[0.12em] font-semibold text-[var(--color-text-3)] mb-3 mt-2">
      {children}
    </h2>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 mb-6">
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  sub,
  on,
  disabled,
  onToggle,
}: {
  label: string;
  sub?: string;
  on: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className="w-full flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0 border-b border-[var(--color-border)] last:border-0 disabled:opacity-50 transition-opacity"
    >
      <span className="text-left">
        <span className="block text-[13.5px] text-[var(--color-text)]">{label}</span>
        {sub && (
          <span className="block text-[12px] text-[var(--color-text-3)] mt-0.5">{sub}</span>
        )}
      </span>
      {/* pill toggle */}
      <span
        aria-hidden
        className={`relative shrink-0 rounded-full transition-colors ${
          on ? "bg-indigo-500" : "bg-[var(--color-border)]"
        }`}
        style={{ width: 40, height: 22 }}
      >
        <span
          className="absolute top-0.5 rounded-full bg-white shadow transition-all"
          style={{ width: 18, height: 18, left: on ? 20 : 2 }}
        />
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// VoiceCard
// ---------------------------------------------------------------------------

function VoiceCard({
  voice,
  selected,
  isDefault,
  onSelect,
}: {
  voice: (typeof VOICE_OPTIONS)[number];
  selected: boolean;
  isDefault: boolean;
  onSelect: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying]       = useState(false);
  const [loading, setLoading]       = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const handlePlay = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (loading) return;

      if (playing && audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        setPlaying(false);
        return;
      }

      setPreviewError(null);
      document
        .querySelectorAll<HTMLAudioElement>("audio[data-voice-preview]")
        .forEach((a) => { a.pause(); a.currentTime = 0; });

      if (!audioRef.current) {
        const audio = new Audio();
        audio.dataset.voicePreview = "true";
        audioRef.current = audio;
        audio.onended = () => setPlaying(false);
        audio.onpause = () => setPlaying(false);
      }

      setLoading(true);
      try {
        const res = await fetch(api.settings.voicePreviewUrl(voice.id), {
          credentials: "include",
        });
        if (res.status === 503) {
          const body = await res.json().catch(() => ({}));
          setPreviewError(body?.detail ?? "ELEVENLABS_API_KEY not configured");
          return;
        }
        if (!res.ok) {
          setPreviewError(`Preview unavailable (HTTP ${res.status})`);
          return;
        }
        const blob = await res.blob();
        const url  = URL.createObjectURL(blob);
        audioRef.current.src = url;
        await audioRef.current.play();
        setPlaying(true);
      } catch {
        setPreviewError("Network error");
      } finally {
        setLoading(false);
      }
    },
    [voice.id, loading, playing],
  );

  return (
    <div
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      aria-pressed={selected}
      className={`relative flex items-center gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
        selected
          ? "border-indigo-500 bg-indigo-500/10"
          : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-indigo-400/60"
      }`}
    >
      {/* selected checkmark */}
      {selected && (
        <span className="absolute top-2 right-2 w-4 h-4 rounded-full bg-indigo-500 flex items-center justify-center">
          <Check className="w-2.5 h-2.5 text-white" />
        </span>
      )}

      <div className="flex-1 min-w-0">
        <p className="text-[13.5px] font-medium text-[var(--color-text)] leading-none mb-1">
          {voice.name}
          {isDefault && (
            <span className="ml-2 inline-flex items-center rounded-full bg-indigo-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-400 leading-none">
              Current
            </span>
          )}
        </p>
        <p className="text-[11.5px] text-[var(--color-text-3)]">{voice.description}</p>
      </div>

      {/* play / stop button */}
      <button
        type="button"
        onClick={handlePlay}
        disabled={loading}
        aria-label={playing ? `Stop ${voice.name}` : `Preview ${voice.name} voice`}
        title={previewError ?? undefined}
        className={`shrink-0 w-8 h-8 rounded-full border flex items-center justify-center transition-colors disabled:opacity-50 ${
          previewError
            ? "bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/15"
            : playing
            ? "bg-indigo-500/10 border-indigo-400"
            : "bg-[var(--color-surface)] border-[var(--color-border)] hover:bg-indigo-500/5 hover:border-indigo-400/60"
        }`}
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin" />
        ) : previewError ? (
          <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
        ) : playing ? (
          <Square className="w-3 h-3 text-indigo-600 fill-indigo-600" />
        ) : (
          <Play className="w-3.5 h-3.5 text-[var(--color-text-2)]" />
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const update = useUpdateSettings();

  const [continuous, setContinuous] = useState(() => readLs(LS_CONTINUOUS, true));
  const [bargeIn,    setBargeIn]    = useState(() => readLs(LS_BARGE_IN,   true));
  const [fastTts,    setFastTts]    = useState(() => readLs(LS_FAST_TTS,   false));
  const [orbMode,    setOrbMode]    = useState(() => readLs(LS_ORB_MODE,   true));
  const [toastVisible, setToastVisible] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Show toast for 2.5 s after each successful save
  useEffect(() => {
    if (!update.isSuccess) return;
    setToastVisible(true);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastVisible(false), 2500);
  }, [update.isSuccess, update.submittedAt]);

  const save = useCallback(
    (patch: Parameters<typeof update.mutate>[0]) => update.mutate(patch),
    [update],
  );

  if (isLoading) {
    return (
      <AppShell>
        <div className="min-h-[50vh] grid place-items-center">
          <div className="h-8 w-8 rounded-full border-2 border-[var(--color-border)] border-t-indigo-600 animate-spin" />
        </div>
      </AppShell>
    );
  }

  if (!settings) return null;

  const selectedVoiceId = settings.elevenlabs_voice_id ?? DEFAULT_VOICE_ID;

  return (
    <AppShell>
      <SavedToast visible={toastVisible} />

      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="mb-7">
          <h1 className="text-2xl font-bold text-[var(--color-text)]">Settings</h1>
          <p className="text-[13.5px] text-[var(--color-text-3)] mt-0.5">
            Manage your AI, voice, and notification preferences
          </p>
        </div>

        {/* ── AI Provider ──────────────────────────────────── */}
        <SectionHeading>AI Provider</SectionHeading>
        <Card>
          <p className="text-[12.5px] text-[var(--color-text-2)] mb-4">
            Choose which LLM powers Pilot.{" "}
            <strong className="text-[var(--color-text)]">Auto</strong> uses Gemini first and
            falls back to Ollama when the free-tier quota runs out.
          </p>
          <div className="space-y-2">
            {(["auto", "gemini", "ollama"] as AiProvider[]).map((p) => {
              const active = settings.ai_provider === p;
              return (
                <label
                  key={p}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    active
                      ? "border-indigo-400 bg-indigo-500/10"
                      : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-indigo-400/60"
                  }`}
                >
                  <input
                    type="radio"
                    name="ai_provider"
                    value={p}
                    checked={active}
                    onChange={() => save({ ai_provider: p })}
                    className="mt-0.5 accent-indigo-500"
                  />
                  <span>
                    <span className="block text-[13.5px] font-medium text-[var(--color-text)]">
                      {p === "auto" ? "Auto (recommended)" : p === "gemini" ? "Gemini" : "Ollama (local)"}
                    </span>
                    <span className="block text-[12px] text-[var(--color-text-3)] mt-0.5">
                      {p === "auto"
                        ? "Gemini → Ollama fallback when quota is reached"
                        : p === "gemini"
                        ? "Always use Gemini (fails when free-tier quota runs out)"
                        : "Always use local Ollama — private, no API key needed"}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>

          {settings.ai_provider === "ollama" && (
            <div className="mt-4">
              <label className="block text-[12.5px] font-medium text-[var(--color-text-2)] mb-1.5">
                Ollama model
              </label>
              <input
                type="text"
                defaultValue={settings.ollama_model ?? "qwen3.5:2b"}
                placeholder="e.g. qwen3.5:2b, llama3.2:3b"
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-[13.5px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
                onBlur={(e) => {
                  const val = e.target.value.trim();
                  if (val && val !== settings.ollama_model) save({ ollama_model: val });
                }}
              />
              <p className="text-[11.5px] text-[var(--color-text-3)] mt-1.5">
                Pull first:{" "}
                <code className="font-mono bg-[var(--color-surface-2)] border border-[var(--color-border)] px-1.5 py-0.5 rounded text-[11px]">
                  ollama pull qwen3.5:2b
                </code>
              </p>
            </div>
          )}
        </Card>

        {/* ── Pilot Voice ──────────────────────────────────── */}
        <SectionHeading>Pilot Voice</SectionHeading>
        <Card>
          <p className="text-[12.5px] text-[var(--color-text-2)] mb-4">
            Click <Play className="inline w-3 h-3 mb-0.5" /> to hear a preview, then click a
            card to select. Requires{" "}
            <code className="font-mono text-[11.5px] bg-[var(--color-surface-2)] border border-[var(--color-border)] px-1.5 py-0.5 rounded">
              ELEVENLABS_API_KEY
            </code>{" "}
            in your .env.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {VOICE_OPTIONS.map((v) => (
              <VoiceCard
                key={v.id}
                voice={v}
                selected={selectedVoiceId === v.id}
                isDefault={v.id === DEFAULT_VOICE_ID}
                onSelect={() => save({ elevenlabs_voice_id: v.id })}
              />
            ))}
          </div>
        </Card>

        {/* ── Voice Agent ──────────────────────────────────── */}
        <SectionHeading>Voice Agent</SectionHeading>
        <Card>
          <ToggleRow
            label="Auto-greet on login"
            sub="Pilot greets you by voice after each new login"
            on={settings.auto_brief_enabled}
            disabled={update.isPending}
            onToggle={() => save({ auto_brief_enabled: !settings.auto_brief_enabled })}
          />
          <ToggleRow
            label='Wake word detection'
            sub='Say "Hey Jarvis" to open voice mode hands-free'
            on={settings.wake_word_enabled}
            disabled={update.isPending}
            onToggle={() => save({ wake_word_enabled: !settings.wake_word_enabled })}
          />
          <ToggleRow
            label="Continuous listening"
            sub="Re-arm mic after Pilot finishes speaking (device setting)"
            on={continuous}
            onToggle={() => { const n = !continuous; setContinuous(n); writeLs(LS_CONTINUOUS, n); }}
          />
          <ToggleRow
            label="Interrupt on speak"
            sub="Cut Pilot off when you start talking (device setting)"
            on={bargeIn}
            onToggle={() => { const n = !bargeIn; setBargeIn(n); writeLs(LS_BARGE_IN, n); }}
          />
          <ToggleRow
            label="Fast browser TTS"
            sub="Lower latency but ignores voice selection above (device setting)"
            on={fastTts}
            onToggle={() => { const n = !fastTts; setFastTts(n); writeLs(LS_FAST_TTS, n); }}
          />
        </Card>

        {/* ── Notifications ────────────────────────────────── */}
        <SectionHeading>Notifications</SectionHeading>
        <Card>
          <ToggleRow
            label="Weekly email digest"
            sub="Receive a Monday summary of your week (applied, offers, streak, DSA)"
            on={settings.digest_opt_in}
            disabled={update.isPending}
            onToggle={() => save({ digest_opt_in: !settings.digest_opt_in })}
          />
          <div className="pt-4 mt-1">
            <label className="block text-[13.5px] font-medium text-[var(--color-text)] mb-1">
              Daily nudge time
            </label>
            <p className="text-[12px] text-[var(--color-text-3)] mb-2">
              Hour you want follow-up reminders delivered (UTC)
            </p>
            <select
              value={settings.nudge_hour ?? ""}
              onChange={(e) => {
                const val = e.target.value === "" ? null : Number(e.target.value);
                save({ nudge_hour: val });
              }}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-[13.5px] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
            >
              <option value="">Server default</option>
              {Array.from({ length: 18 }, (_, i) => i + 6).map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, "0")}:00 UTC
                </option>
              ))}
            </select>
          </div>
        </Card>

        {/* ── Interview ────────────────────────────────────── */}
        <SectionHeading>Interview</SectionHeading>
        <Card>
          <ToggleRow
            label="Orb mode"
            sub="Show the animated AI orb during mock interviews instead of text questions (default: on)"
            on={orbMode}
            onToggle={() => { const n = !orbMode; setOrbMode(n); writeLs(LS_ORB_MODE, n); }}
          />
        </Card>

        {/* ── Goals ────────────────────────────────────────── */}
        <SectionHeading>Goals</SectionHeading>
        <Card>
          <label className="block text-[13.5px] font-medium text-[var(--color-text)] mb-1">
            Weekly application target
          </label>
          <p className="text-[12px] text-[var(--color-text-3)] mb-3">
            How many jobs you want to apply to each week. Shown as a progress bar on your
            dashboard.
          </p>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={1}
              max={50}
              step={1}
              defaultValue={settings.weekly_apps_goal}
              className="flex-1 accent-indigo-500"
              onMouseUp={(e) =>
                save({ weekly_apps_goal: Number((e.target as HTMLInputElement).value) })
              }
              onTouchEnd={(e) =>
                save({ weekly_apps_goal: Number((e.target as HTMLInputElement).value) })
              }
            />
            <span className="w-10 text-center text-[15px] font-semibold text-indigo-600 tabular-nums">
              {settings.weekly_apps_goal}
            </span>
          </div>
          <p className="text-[11.5px] text-[var(--color-text-3)] mt-1.5">
            {settings.weekly_apps_goal} apps / week
          </p>
        </Card>
      </div>
    </AppShell>
  );
}

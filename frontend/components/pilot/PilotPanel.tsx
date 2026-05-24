"use client";

import {
  AudioLines,
  ChevronDown,
  Mic,
  Send,
  Sparkles,
  Trash2,
  Volume2,
  VolumeX,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useGamifyState } from "@/hooks/useGamify";
import { useMe } from "@/hooks/useMe";
import { useVoiceAgent, type AgentTurn } from "@/hooks/useVoiceAgent";
import type { PilotToolTrace } from "@/lib/api";

export function PilotPanel({
  agent,
  open,
  greeting,
  onClose,
  onOpenVoiceMode,
}: {
  agent: ReturnType<typeof useVoiceAgent>;
  open: boolean;
  greeting: string | null;
  onClose: () => void;
  onOpenVoiceMode?: () => void;
}) {
  const { data: me } = useMe();
  const { data: state } = useGamifyState();
  const [text, setText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const greetingPlayedRef = useRef(false);

  const firstName = (me?.display_name ?? "").split(" ")[0] || "there";
  const suggestions = pickSuggestions(state?.streak ?? 0);

  // Auto-scroll on history change.
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [agent.history.length, agent.status]);

  // Speak greeting on first open (user gesture unlocks audio).
  useEffect(() => {
    if (!open || greetingPlayedRef.current || !greeting) return;
    greetingPlayedRef.current = true;
    agent.speak(greeting);
  }, [open, greeting, agent]);

  // Close on ESC.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        agent.cancel();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose, agent]);

  if (!open) return null;

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const value = text.trim();
    if (!value) return;
    setText("");
    await agent.sendText(value);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Pilot — voice assistant"
      className="fixed bottom-6 right-6 z-50 w-[calc(100vw-3rem)] max-w-[360px] h-[min(520px,calc(100vh-6rem))] rounded-2xl bg-[var(--color-surface)] shadow-2xl ring-1 ring-[var(--color-border)] flex flex-col overflow-hidden fade-up"
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] bg-gradient-to-r from-indigo-500/10 via-violet-500/10 to-fuchsia-500/10">
        <div className="flex items-center gap-2 min-w-0">
          <span className="grid place-items-center w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-[12px] font-bold">
            P
          </span>
          <div className="min-w-0">
            <div className="text-[14px] font-semibold text-[var(--color-text)]">Pilot</div>
            <div className="text-[11px] text-[var(--color-text-3)]">
              <StatusLabel status={agent.status} />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          {onOpenVoiceMode ? (
            <button
              type="button"
              onClick={onOpenVoiceMode}
              className="p-1.5 rounded-md text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
              aria-label="Open voice mode"
              title="Voice mode"
            >
              <AudioLines className="w-4 h-4" />
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => agent.setVoiceEnabled(!agent.voiceEnabled)}
            className="p-1.5 rounded-md text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
            aria-label={agent.voiceEnabled ? "Mute Pilot" : "Unmute Pilot"}
            title={agent.voiceEnabled ? "Mute voice" : "Enable voice"}
          >
            {agent.voiceEnabled ? (
              <Volume2 className="w-4 h-4" />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
          </button>
          <button
            type="button"
            onClick={agent.clearHistory}
            className="p-1.5 rounded-md text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
            aria-label="Clear conversation"
            title="Clear conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              agent.cancel();
              onClose();
            }}
            className="p-1.5 rounded-md text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3.5 py-3 space-y-2.5"
      >
        {agent.history.length === 0 ? (
          <WelcomeIntro
            firstName={firstName}
            greeting={greeting}
            suggestions={suggestions}
            onPick={(q) => agent.sendText(q)}
          />
        ) : null}
        {agent.history.map((t) => (
          <BubbleWithTrace key={t.id} turn={t} />
        ))}
        {agent.error ? (
          <div className="text-[12px] text-red-600 px-2">{agent.error}</div>
        ) : null}
      </div>

      <form
        onSubmit={submit}
        className="border-t border-[var(--color-border)] p-2.5 flex items-end gap-2"
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder="Type or hold the mic…"
          disabled={agent.status === "recording"}
          className="flex-1 resize-none bg-[var(--color-surface-2)] rounded-lg px-3 py-2 text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:opacity-50"
        />
        <MicButton agent={agent} />
        <button
          type="submit"
          disabled={!text.trim() || agent.status !== "idle"}
          aria-label="Send"
          className="grid place-items-center w-9 h-9 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}

function MicButton({ agent }: { agent: ReturnType<typeof useVoiceAgent> }) {
  const recording = agent.status === "recording";
  const busy =
    agent.status === "transcribing" ||
    agent.status === "thinking" ||
    agent.status === "speaking";

  const onPointerDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.preventDefault();
    if (busy) return;
    agent.startRecording();
  };
  const onPointerUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.preventDefault();
    if (recording) agent.stopRecording();
  };

  return (
    <button
      type="button"
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onPointerLeave={recording ? onPointerUp : undefined}
      disabled={busy}
      aria-label={recording ? "Release to send" : "Hold to talk"}
      className={`grid place-items-center w-9 h-9 rounded-lg transition-colors disabled:opacity-40 ${
        recording
          ? "bg-red-600 text-white ring-4 ring-red-200 animate-pulse"
          : "bg-gray-900 text-white hover:bg-gray-800"
      }`}
    >
      <Mic className="w-4 h-4" />
    </button>
  );
}

function Bubble({
  role,
  pending,
  children,
}: {
  role: "user" | "assistant";
  pending?: boolean;
  children: React.ReactNode;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3 py-2 text-[13px] leading-snug ${
          isUser
            ? "bg-indigo-600 text-white rounded-br-sm"
            : "bg-[var(--color-surface-2)] text-[var(--color-text)] rounded-bl-sm"
        }`}
      >
        {pending ? <TypingDots /> : children}
      </div>
    </div>
  );
}

function BubbleWithTrace({ turn }: { turn: AgentTurn }) {
  const trace = turn.tool_trace;
  return (
    <div className="space-y-1">
      <Bubble role={turn.role} pending={turn.pending}>
        {turn.content}
      </Bubble>
      {turn.role === "assistant" && trace && trace.length > 0 ? (
        <ToolTraceFooter trace={trace} />
      ) : null}
    </div>
  );
}

function ToolTraceFooter({ trace }: { trace: PilotToolTrace[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] w-full">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1 text-[10.5px] text-[var(--color-text-3)] hover:text-[var(--color-text-2)] px-1.5 py-0.5 rounded transition-colors"
          aria-expanded={open}
        >
          <Wrench className="w-3 h-3" />
          <span>
            Pilot checked {trace.length}{" "}
            {trace.length === 1 ? "source" : "sources"}
          </span>
          <ChevronDown
            className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
          />
        </button>
        {open ? (
          <ul className="mt-1 space-y-1">
            {trace.map((t, i) => (
              <li
                key={i}
                className="rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] px-2 py-1.5 text-[11px]"
              >
                <div className="flex items-center gap-1.5 font-semibold text-[var(--color-text-2)]">
                  <span className="text-indigo-400">{t.name}</span>
                  <span className="text-[var(--color-text-3)] tabular-nums">
                    · {t.latency_ms}ms
                  </span>
                </div>
                {Object.keys(t.args || {}).length > 0 ? (
                  <div className="mt-0.5 text-[var(--color-text-3)] truncate">
                    {summariseArgs(t.args)}
                  </div>
                ) : null}
                <div className="mt-0.5 text-[var(--color-text-3)] truncate">
                  {summariseResult(t.result)}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

function summariseArgs(args: Record<string, unknown>): string {
  const pairs = Object.entries(args)
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${formatVal(v)}`);
  return pairs.join(", ");
}

function summariseResult(result: Record<string, unknown>): string {
  if (typeof result === "object" && result !== null) {
    if ("error" in result) return `error: ${formatVal(result.error)}`;
    if ("ambiguous" in result) return "ambiguous — multiple matches";
    if ("count" in result) return `${result.count} record(s)`;
    const keys = Object.keys(result).slice(0, 3);
    if (keys.length) return keys.join(", ");
  }
  return "ok";
}

function formatVal(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v.length > 30 ? v.slice(0, 28) + "…" : v;
  if (typeof v === "object") return JSON.stringify(v).slice(0, 40);
  return String(v);
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-3)] animate-bounce [animation-delay:-0.2s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-3)] animate-bounce [animation-delay:-0.1s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-3)] animate-bounce" />
    </span>
  );
}

function StatusLabel({
  status,
}: {
  status: ReturnType<typeof useVoiceAgent>["status"];
}) {
  switch (status) {
    case "recording":
      return <span className="text-red-600">Listening…</span>;
    case "transcribing":
      return <span>Transcribing…</span>;
    case "thinking":
      return <span>Thinking…</span>;
    case "speaking":
      return <span className="text-indigo-600">Speaking…</span>;
    default:
      return <span>Ready</span>;
  }
}

function WelcomeIntro({
  firstName,
  greeting,
  suggestions,
  onPick,
}: {
  firstName: string;
  greeting: string | null;
  suggestions: string[];
  onPick: (q: string) => void;
}) {
  return (
    <div className="fade-up flex flex-col items-center text-center pt-2 pb-1">
      <span className="relative grid place-items-center w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-white shadow-lg ring-4 ring-[var(--color-surface)]">
        <Sparkles className="w-5 h-5" />
        <span
          aria-hidden
          className="absolute inset-0 rounded-full bg-white/10 animate-ping"
        />
      </span>
      <h3 className="mt-3 text-[15px] font-semibold text-[var(--color-text)]">
        Hi {firstName}.
      </h3>
      <p className="mt-1 text-[12.5px] text-[var(--color-text-3)] leading-snug max-w-[260px]">
        {greeting
          ? greeting
          : "I keep track of your job hunt and help you think through it. Try one of these:"}
      </p>
      <ul className="mt-3.5 w-full space-y-1.5">
        {suggestions.map((q) => (
          <li key={q}>
            <button
              type="button"
              onClick={() => onPick(q)}
              className="w-full text-left rounded-lg ring-1 ring-[var(--color-border)] bg-[var(--color-surface)] hover:ring-indigo-500/40 hover:bg-indigo-500/10 px-3 py-2 text-[12.5px] text-[var(--color-text)] transition-colors"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function pickSuggestions(streak: number): string[] {
  if (streak === 0) {
    return [
      "What should I focus on today?",
      "How do I start a streak?",
      "I just got rejected. What now?",
    ];
  }
  if (streak < 7) {
    return [
      "How am I doing this week?",
      "What should I focus on today?",
      "I just got rejected. What now?",
    ];
  }
  return [
    "How am I doing this week?",
    "Where am I leaking applications?",
    "I'm burned out. What now?",
  ];
}

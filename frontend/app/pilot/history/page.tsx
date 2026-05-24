"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Wrench, History as HistoryIcon } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { api, type PilotHistoryTurn, type PilotToolTrace } from "@/lib/api";

/**
 * /pilot/history — chronological audit of what Pilot did on the user's
 * behalf. Each turn shows the spoken-text and (for assistant turns) an
 * expandable tool trace with args + result + latency.
 *
 * This is the trust surface. If a user ever wonders "did Pilot really
 * delete that?", the answer is here.
 */
export default function PilotHistoryPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["pilot", "history"],
    queryFn: () => api.pilot.history(100),
    staleTime: 30_000,
  });

  return (
    <AppShell>
      <main className="flex-1 flex flex-col">
        <div className="max-w-3xl w-full mx-auto px-6 pt-8 pb-16 flex-1">
          <header className="mb-6">
            <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.18em] text-[var(--color-text-3)]">
              <HistoryIcon className="w-3.5 h-3.5" />
              <span>Pilot history</span>
            </div>
            <h1 className="mt-1 text-[26px] font-bold tracking-tight text-[var(--color-text)]">
              What Pilot did on your behalf
            </h1>
            <p className="text-[14px] text-[var(--color-text-3)] mt-1">
              Every voice turn, in order. Expand any reply to see the
              tools Pilot called, the arguments it passed, and what came
              back.
            </p>
          </header>

          {isLoading ? <SkeletonList /> : null}

          {error ? (
            <div className="rounded-xl ring-1 ring-rose-500/20 bg-rose-500/10 px-4 py-3 text-[13.5px] text-rose-400">
              {error instanceof Error ? error.message : "Couldn't load history."}
            </div>
          ) : null}

          {data && data.turns.length === 0 ? <EmptyState /> : null}

          {data && data.turns.length > 0 ? (
            <ol className="space-y-3">
              {data.turns.map((t) => (
                <TurnRow key={t.id} turn={t} />
              ))}
            </ol>
          ) : null}
        </div>
      </main>
    </AppShell>
  );
}

function TurnRow({ turn }: { turn: PilotHistoryTurn }) {
  const [open, setOpen] = useState(false);
  const isUser = turn.role === "user";
  const ts = new Date(turn.created_at);
  const time = ts.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const date = ts.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
  const traceCount = turn.tool_calls?.length ?? 0;

  return (
    <li
      className={`rounded-xl ring-1 px-4 py-3 ${
        isUser
          ? "bg-indigo-500/10 ring-indigo-500/20"
          : "bg-[var(--color-surface)] ring-[var(--color-border)]"
      }`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span
          className={`text-[10.5px] uppercase tracking-[0.18em] ${
            isUser ? "text-indigo-400" : "text-[var(--color-text-3)]"
          }`}
        >
          {isUser ? "You" : "Pilot"}
        </span>
        <span className="text-[11px] text-[var(--color-text-3)] tabular-nums">
          {date} · {time}
        </span>
      </div>
      <p
        className={`mt-1 text-[14px] leading-snug ${
          isUser ? "text-[var(--color-text)]" : "text-[var(--color-text)]"
        }`}
      >
        {turn.content || (
          <span className="italic text-[var(--color-text-3)]">(empty)</span>
        )}
      </p>

      {traceCount > 0 ? (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="inline-flex items-center gap-1.5 text-[11.5px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
            aria-expanded={open}
          >
            <Wrench className="w-3 h-3" />
            <span>
              Pilot used {traceCount} tool{traceCount === 1 ? "" : "s"}
            </span>
            {open ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </button>
          {open ? (
            <ul className="mt-2 space-y-1.5">
              {turn.tool_calls!.map((t, i) => (
                <TraceRow key={i} trace={t} />
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function TraceRow({ trace }: { trace: PilotToolTrace }) {
  return (
    <li className="rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] px-3 py-2 text-[12px]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-indigo-400">{trace.name}</span>
        <span className="text-[11px] text-[var(--color-text-3)] tabular-nums">
          {trace.latency_ms}ms
        </span>
      </div>
      {Object.keys(trace.args || {}).length > 0 ? (
        <pre className="mt-1 text-[11.5px] text-[var(--color-text-2)] whitespace-pre-wrap break-words">
          <span className="text-[var(--color-text-3)]">args </span>
          {JSON.stringify(trace.args, null, 0)}
        </pre>
      ) : null}
      <pre className="mt-0.5 text-[11.5px] text-[var(--color-text-2)] whitespace-pre-wrap break-words">
        <span className="text-[var(--color-text-3)]">result </span>
        {summariseResult(trace.result)}
      </pre>
    </li>
  );
}

function summariseResult(result: Record<string, unknown>): string {
  if (!result || typeof result !== "object") return String(result);
  if ("error" in result) return `error: ${String(result.error)}`;
  if ("needs_confirmation" in result) {
    return `needs_confirmation (summary: ${String(result.summary ?? "")})`;
  }
  // For verbose results, just show the top-level keys so the page
  // doesn't drown in JSON. Click-through detail can come later.
  const keys = Object.keys(result);
  if (keys.length === 0) return "ok";
  if (keys.length <= 4) return JSON.stringify(result);
  return `{${keys.slice(0, 4).join(", ")}, …}`;
}

function SkeletonList() {
  return (
    <ul className="space-y-3">
      {[0, 1, 2, 3].map((i) => (
        <li
          key={i}
          className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] px-4 py-3 animate-pulse"
        >
          <div className="h-3 w-16 bg-[var(--color-surface-2)] rounded" />
          <div className="mt-2 h-4 w-3/4 bg-[var(--color-surface-2)] rounded" />
        </li>
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl ring-1 ring-[var(--color-border)] bg-[var(--color-surface)] px-6 py-10 text-center">
      <p className="text-[14px] text-[var(--color-text-2)]">No voice turns yet.</p>
      <p className="mt-1 text-[12.5px] text-[var(--color-text-3)]">
        Open the voice agent and start talking — every turn will land here.
      </p>
    </div>
  );
}

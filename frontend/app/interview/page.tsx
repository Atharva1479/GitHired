"use client";
import { ChevronRight, Clock, Mic, Trash2, Trophy, X, Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import SetupForm from "@/components/interview/SetupForm";
import { useDeleteSession, useHistory } from "@/hooks/useInterview";

function BottomHistory() {
  const { data: sessions, isLoading } = useHistory();
  const { mutate: deleteSession, isPending: isDeleting } = useDeleteSession();
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const hasSessions = (sessions?.length ?? 0) > 0;

  return (
    <div className="border-t border-[var(--color-border)]">
      <div className="max-w-3xl mx-auto px-6 pt-6 pb-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-[var(--color-text-3)]" />
            <span className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-3)]">
              Recent Sessions
            </span>
            {hasSessions && (
              <span className="text-[10px] bg-indigo-500/10 text-indigo-500 font-bold px-1.5 py-0.5 rounded-full">
                {sessions!.length}
              </span>
            )}
          </div>
          {hasSessions && (
            <Link
              href="/interview/history"
              className="text-xs text-indigo-500 hover:text-indigo-400 flex items-center gap-1 transition-colors"
            >
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          )}
        </div>

        {/* Skeletons */}
        {isLoading && (
          <div className="flex gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-24 w-44 shrink-0 rounded-2xl bg-[var(--color-border)] animate-pulse opacity-40"
              />
            ))}
          </div>
        )}

        {/* Empty */}
        {!isLoading && !hasSessions && (
          <div className="flex items-center gap-3 py-3">
            <Trophy className="w-4 h-4 text-[var(--color-text-3)] shrink-0" />
            <p className="text-sm text-[var(--color-text-3)]">
              No sessions yet — your completed interviews will appear here.
            </p>
          </div>
        )}

        {/* Cards */}
        {hasSessions && (
          <div className="flex gap-3 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
            {sessions!.slice(0, 12).map((s) => {
              const isConfirming = confirmId === s.id;
              return (
                <div
                  key={s.id}
                  className="group shrink-0 w-44 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] hover:border-indigo-400 hover:shadow-md hover:shadow-indigo-500/5 transition-all overflow-hidden"
                >
                  {/* Colored top strip */}
                  <div className={`h-1 w-full ${s.status === "ended" ? "bg-emerald-500" : "bg-amber-400"}`} />

                  {isConfirming ? (
                    /* ── Confirm delete ── */
                    <div className="p-3.5 flex flex-col justify-between h-[calc(100%-4px)]">
                      <p className="text-xs font-semibold text-[var(--color-text)] mb-3">
                        Delete this session?
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            deleteSession(s.id, { onSuccess: () => setConfirmId(null) });
                          }}
                          disabled={isDeleting}
                          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-red-500 text-white text-xs font-semibold hover:bg-red-600 disabled:opacity-50 transition-colors"
                        >
                          <Check className="w-3 h-3" /> Yes
                        </button>
                        <button
                          onClick={() => setConfirmId(null)}
                          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg border border-[var(--color-border)] text-xs font-semibold hover:border-[var(--color-text-3)] transition-colors"
                        >
                          <X className="w-3 h-3" /> No
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* ── Normal card ── */
                    <div className="p-3.5 relative">
                      {/* Delete button — visible on hover */}
                      <button
                        onClick={(e) => { e.preventDefault(); setConfirmId(s.id); }}
                        className="absolute top-2.5 right-2.5 w-6 h-6 rounded-md flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-500 text-[var(--color-text-3)] transition-all"
                        title="Delete session"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      {/* Status + date */}
                      <div className="flex items-center gap-1.5 mb-2.5">
                        <span className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-md ${
                          s.status === "ended"
                            ? "bg-emerald-500/10 text-emerald-500"
                            : "bg-amber-500/10 text-amber-500"
                        }`}>
                          {s.status === "ended" ? "Done" : "Live"}
                        </span>
                        <span className="text-[10px] text-[var(--color-text-3)]">
                          {new Date(s.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </span>
                      </div>

                      {/* Topic — navigates to report */}
                      <Link href={`/interview/report/${s.id}`} className="block">
                        <p className="text-sm font-semibold leading-snug text-[var(--color-text)] line-clamp-2 hover:text-indigo-500 transition-colors">
                          {s.topic}
                        </p>
                        <p className="text-xs text-[var(--color-text-3)] mt-1 truncate">{s.role}</p>
                      </Link>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default function InterviewSetupPage() {
  return (
    <AppShell>
      <div className="flex flex-col min-h-[calc(100vh-56px)]">

        {/* ── Hero ── */}
        <div className="relative overflow-hidden shrink-0">
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-600/15 via-indigo-600/4 to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(99,102,241,0.12),transparent)] pointer-events-none" />
          <div className="relative text-center px-6 pt-12 pb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-500/40 mb-5">
              <Mic className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">AI Mock Interview</h1>
            <p className="text-[var(--color-text-2)] mt-2 text-sm max-w-xs mx-auto leading-relaxed">
              Practice out loud. Get scored on every answer. Know exactly what to improve.
            </p>
          </div>
        </div>

        {/* ── Form ── */}
        <div className="flex-1 max-w-3xl w-full mx-auto px-6 py-8">
          <SetupForm />
        </div>

        {/* ── History at bottom ── */}
        <BottomHistory />
      </div>
    </AppShell>
  );
}

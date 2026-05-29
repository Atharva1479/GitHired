"use client";
import { useEffect, useState } from "react";
import { AlertCircle, Trophy, ArrowLeft, Briefcase, Flame, Zap, Sparkles, Search } from "lucide-react";
import { useSkillGap } from "@/hooks/useResumes";
import type { SkillGap } from "@/lib/resumes-api";

interface Props {
  resumeId: number;
  resumeName: string;
  roleTag: string;
  onBack: () => void;
}

function pct(g: SkillGap) {
  return Math.round((g.frequency / g.total_jobs) * 100);
}

const TIERS = [
  {
    key: "critical",
    label: "Must Add",
    sub: "Appear in 70%+ of your matched jobs",
    icon: Flame,
    chipClass: "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/15",
    pctClass: "text-red-400",
    headerClass: "text-red-400",
    dotClass: "bg-red-500",
  },
  {
    key: "high",
    label: "Should Add",
    sub: "Appear in 40–70% of your matched jobs",
    icon: Zap,
    chipClass: "bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/15",
    pctClass: "text-amber-400",
    headerClass: "text-amber-400",
    dotClass: "bg-amber-500",
  },
  {
    key: "medium",
    label: "Nice to Have",
    sub: "Appear in under 40% of your matched jobs",
    icon: Sparkles,
    chipClass: "bg-[var(--color-surface-2)] text-[var(--color-text-2)] border-[var(--color-border)] hover:border-indigo-400/30 hover:bg-indigo-500/5",
    pctClass: "text-indigo-400",
    headerClass: "text-indigo-400",
    dotClass: "bg-indigo-400",
  },
];

export function SkillGapPanel({ resumeId, resumeName, roleTag, onBack }: Props) {
  const { data, isLoading, error } = useSkillGap(resumeId);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (data) { setReady(false); const t = setTimeout(() => setReady(true), 60); return () => clearTimeout(t); }
  }, [data]);

  if (isLoading) return (
    <div className="flex flex-col items-center justify-center py-24 gap-3 text-[var(--color-text-3)]">
      <Search className="w-8 h-8 animate-pulse text-indigo-400" />
      <p className="text-[13px]">Scanning {resumeName}…</p>
    </div>
  );

  if (error) return (
    <div className="flex flex-col items-center gap-3 py-16 text-red-400">
      <AlertCircle className="w-7 h-7" />
      <p className="text-[13px]">{error instanceof Error ? error.message : "Failed to load"}</p>
      <button onClick={onBack} className="text-[12px] text-[var(--color-text-3)] hover:text-[var(--color-text)]">← Back</button>
    </div>
  );

  if (!data) return null;

  const critical = data.gaps.filter(g => pct(g) >= 70);
  const high     = data.gaps.filter(g => { const p = pct(g); return p >= 40 && p < 70; });
  const medium   = data.gaps.filter(g => pct(g) < 40);
  const groups   = [critical, high, medium];

  return (
    <div className="space-y-6">

      {/* ── nav bar ── */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[12px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> All resumes
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-[13px] font-semibold">{resumeName}</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-400/20">{roleTag}</span>
        </div>
        <span className="text-[11px] text-[var(--color-text-3)]">{data.matched_jobs} jobs</span>
      </div>

      {/* ── no jobs ── */}
      {data.matched_jobs === 0 && (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-amber-400" />
          </div>
          <p className="text-[13px] font-semibold">No matching applications</p>
          <p className="text-[12px] text-[var(--color-text-3)] max-w-xs leading-relaxed">
            Add applications with role matching <span className="font-medium text-[var(--color-text-2)]">{roleTag}</span> and paste their JDs.
          </p>
        </div>
      )}

      {/* ── all covered ── */}
      {data.matched_jobs > 0 && data.gaps.length === 0 && (
        <div className="flex flex-col items-center py-16 gap-3">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
            <Trophy className="w-7 h-7 text-emerald-400" />
          </div>
          <p className="text-[15px] font-bold text-emerald-500">No gaps — resume looks solid!</p>
          <p className="text-[12px] text-[var(--color-text-3)]">Covers all skills across {data.matched_jobs} matched jobs.</p>
        </div>
      )}

      {/* ── summary stat row ── */}
      {data.matched_jobs > 0 && data.gaps.length > 0 && (
        <>
          <div className="grid grid-cols-3 gap-3">
            {TIERS.map((tier, ti) => {
              const count = groups[ti].length;
              const Icon = tier.icon;
              return (
                <div
                  key={tier.key}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-center"
                  style={{ opacity: ready ? 1 : 0, transition: `opacity 0.25s ${ti * 60}ms` }}
                >
                  <div className={`flex items-center justify-center gap-1.5 mb-1 ${tier.headerClass}`}>
                    <Icon className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-black uppercase tracking-widest">{tier.label}</span>
                  </div>
                  <p className={`text-[28px] font-black tabular-nums leading-none ${count === 0 ? "text-[var(--color-text-3)]" : tier.headerClass}`}>{count}</p>
                  <p className="text-[10px] text-[var(--color-text-3)] mt-1">skill{count !== 1 ? "s" : ""}</p>
                </div>
              );
            })}
          </div>

          {/* ── tier sections ── */}
          <div className="space-y-5">
            {TIERS.map((tier, ti) => {
              const skills = groups[ti];
              if (skills.length === 0) return null;
              const Icon = tier.icon;
              return (
                <div key={tier.key}>
                  {/* section header */}
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`w-2 h-2 rounded-full ${tier.dotClass}`} />
                    <Icon className={`w-3.5 h-3.5 ${tier.headerClass}`} />
                    <span className={`text-[11px] font-black uppercase tracking-widest ${tier.headerClass}`}>{tier.label}</span>
                    <span className="text-[10px] text-[var(--color-text-3)]">— {tier.sub}</span>
                  </div>

                  {/* chip wrap */}
                  <div className="flex flex-wrap gap-2">
                    {skills.map((g, i) => (
                      <span
                        key={g.skill}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-[12.5px] font-semibold capitalize transition-colors cursor-default ${tier.chipClass}`}
                        style={{
                          opacity: ready ? 1 : 0,
                          transform: ready ? "scale(1)" : "scale(0.92)",
                          transition: `opacity 0.2s ${ti * 80 + i * 25}ms, transform 0.2s ${ti * 80 + i * 25}ms`,
                        }}
                      >
                        {g.skill}
                        <span className={`text-[10px] font-black tabular-nums ${tier.pctClass}`}>{pct(g)}%</span>
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

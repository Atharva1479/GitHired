"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Lightbulb,
  Loader2,
  ThumbsUp,
  TrendingUp,
  Wand2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { ScoreGauge } from "@/components/ats/ScoreGauge";
import { TailorPanel } from "@/components/ats/TailorPanel";
import type { ATSFeedback } from "@/lib/ats-api";
import { getAtsFeedback, tailorResume } from "@/lib/ats-api";
import type { AnalysisResult, CategoryScore, TailorSuggestion } from "@/types/ats";

/* ── helpers ──────────────────────────────────────────────────────── */

function verdict(score: number): { label: string; cls: string } {
  if (score >= 80) return { label: "Strong Match",  cls: "bg-emerald-500/10 text-emerald-600 ring-emerald-300/40" };
  if (score >= 65) return { label: "Good Match",    cls: "bg-blue-500/10    text-blue-600    ring-blue-300/40"    };
  if (score >= 50) return { label: "Fair Match",    cls: "bg-amber-500/10   text-amber-600   ring-amber-300/40"  };
  return               { label: "Needs Work",    cls: "bg-red-500/10     text-red-600     ring-red-300/40"    };
}


function barColor(score: number) {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function scoreText(score: number) {
  if (score >= 70) return "text-emerald-500";
  if (score >= 50) return "text-amber-500";
  return "text-red-500";
}

const ML_KEYS = new Set(["semantic_sentence", "word_semantic"]);

const SECTION_PILL: Record<string, string> = {
  skills:     "bg-emerald-500/10 text-emerald-700 ring-emerald-300/40",
  experience: "bg-blue-500/10    text-blue-700    ring-blue-300/40",
  summary:    "bg-violet-500/10  text-violet-700  ring-violet-300/40",
};
function sectionPill(sec: string) {
  return SECTION_PILL[sec.toLowerCase()] ?? "bg-[var(--color-surface-2)] text-[var(--color-text-2)] ring-[var(--color-border)]";
}

/* ── page ─────────────────────────────────────────────────────────── */

export default function AtsResultsPage() {
  const router  = useRouter();
  const [result, setResult]       = useState<AnalysisResult | null>(null);
  const [hydrated, setHydrated]   = useState(false);
  const [barsReady, setBarsReady] = useState(false);
  const [feedback, setFeedback]   = useState<ATSFeedback | null>(null);
  const [fbLoading, setFbLoading] = useState(false);
  const [jdText, setJdText]                           = useState("");
  const [tailorOpen, setTailorOpen]                   = useState(false);
  const [tailorLoading, setTailorLoading]             = useState(false);
  const [tailorSuggestions, setTailorSuggestions]     = useState<TailorSuggestion[]>([]);
  const [tailorError, setTailorError]                 = useState<string | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("ats_result");
    if (!raw) { router.replace("/ats"); return; }
    try {
      const parsed = JSON.parse(raw) as AnalysisResult;
      setResult(parsed);
      setJdText(localStorage.getItem("ats_jd_text") ?? "");
      setHydrated(true);
      setTimeout(() => setBarsReady(true), 120);

      setFbLoading(true);
      getAtsFeedback(parsed)
        .then(setFeedback)
        .catch(() => setFeedback(null))
        .finally(() => setFbLoading(false));
    } catch {
      router.replace("/ats");
    }
  }, [router]);

  async function runTailor() {
    if (!result) return;
    setTailorOpen(true);
    setTailorLoading(true);
    setTailorError(null);
    setTailorSuggestions([]);
    try {
      const res = await tailorResume({
        resume_text: result.resume_text ?? "",
        jd_text: jdText,
        required_missing: result.required_missing,
        preferred_missing: result.preferred_missing,
      });
      setTailorSuggestions(res.suggestions);
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : "Couldn't generate rewrites");
    } finally {
      setTailorLoading(false);
    }
  }

  if (!hydrated || !result) {
    return (
      <div className="min-h-[60dvh] grid place-items-center">
        <div className="h-9 w-9 rounded-full border-2 border-[var(--color-border)] border-t-indigo-600 animate-spin" />
      </div>
    );
  }

  const {
    overall_score, grade, categories, keyword_stats,
    keyword_placement, required_missing, preferred_missing,
    synonym_matches, word_semantic_matches, semantic_matches,
    experience_data, occupation_context, ml_status,
  } = result;

  const v = verdict(overall_score);

  const bySection: Record<string, string[]> = {};
  for (const [kw, placement] of Object.entries(keyword_placement)) {
    const sec = placement.section.toLowerCase();
    if (!bySection[sec]) bySection[sec] = [];
    bySection[sec].push(kw);
  }

  const requiredFound   = result.jd_structure.required_count  - (result.keyword_stats.required_missing_count  ?? required_missing.length);
  const preferredFound  = result.jd_structure.preferred_count - preferred_missing.length;

  function handleAnalyzeAnother() {
    localStorage.removeItem("ats_result");
    router.push("/ats");
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">

        {/* ── TOPBAR ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleAnalyzeAnother}
            className="inline-flex items-center gap-1.5 text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Analyze Another
          </button>
          <h1 className="text-[16px] font-bold text-[var(--color-text)]">ATS Score Report</h1>
          <button
            type="button"
            onClick={handleAnalyzeAnother}
            className="text-[12px] px-3 py-1.5 rounded-lg ring-1 ring-[var(--color-border)] text-[var(--color-text-3)] hover:bg-[var(--color-surface-2)] transition-colors"
          >
            + New scan
          </button>
        </div>

        {/* ── SCORE HERO ──────────────────────────────────────────── */}
        <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-6">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">

            <div className="shrink-0">
              <ScoreGauge score={overall_score} grade={grade} />
            </div>

            <div className="flex-1 w-full">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className={`text-[13px] font-bold px-3 py-1 rounded-full ring-1 ${v.cls}`}>
                  {v.label}
                </span>
                {ml_status.semantic_sentence_active ? (
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-600 ring-1 ring-indigo-300/40">
                    <Brain className="w-3 h-3" />Semantic ML
                  </span>
                ) : null}
                {ml_status.word_semantic_active ? (
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-600 ring-1 ring-violet-300/40">
                    <Cpu className="w-3 h-3" />Word2Vec
                  </span>
                ) : null}
              </div>

              {occupation_context.detected_title && (
                <p className="text-[13px] text-[var(--color-text-3)] mb-4">
                  Detected role:{" "}
                  <span className="font-semibold text-[var(--color-text)]">
                    {occupation_context.detected_title}
                  </span>
                  {occupation_context.implicit_skills_added.length > 0 && (
                    <span className="text-indigo-500">
                      {" "}+{occupation_context.implicit_skills_added.length} implicit skills
                    </span>
                  )}
                </p>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <StatCard
                  label="Required Keywords"
                  value={`${requiredFound} / ${result.jd_structure.required_count}`}
                  sub={requiredFound === result.jd_structure.required_count ? "All matched" : `${result.jd_structure.required_count - requiredFound} missing`}
                  tone={requiredFound === result.jd_structure.required_count ? "green" : "red"}
                />
                <StatCard
                  label="Preferred Keywords"
                  value={`${preferredFound} / ${result.jd_structure.preferred_count}`}
                  sub={preferredFound === result.jd_structure.preferred_count ? "All matched" : `${preferred_missing.length} missing`}
                  tone={preferredFound === result.jd_structure.preferred_count ? "green" : "amber"}
                />
                <StatCard
                  label="Total Matched"
                  value={`${keyword_stats.matched_count}`}
                  sub={`${keyword_stats.match_percentage.toFixed(0)}% of JD keywords`}
                  tone="blue"
                />
                <StatCard
                  label="Experience"
                  value={`${experience_data.total_years} yrs`}
                  sub={
                    experience_data.required_years != null
                      ? experience_data.total_years >= experience_data.required_years
                        ? "Meets requirement"
                        : `Need ${experience_data.required_years} yrs`
                      : "No requirement stated"
                  }
                  tone={
                    experience_data.required_years == null ||
                    experience_data.total_years >= experience_data.required_years
                      ? "green"
                      : "amber"
                  }
                />
              </div>
            </div>
          </div>
        </div>

        {/* ── SCORE BREAKDOWN + KEYWORD OVERVIEW ───────────────── */}
        <div className="grid md:grid-cols-5 gap-5">

          <div className="md:col-span-3 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-5">
            <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-5">
              Score Breakdown
            </h2>
            <div className="space-y-4">
              {(Object.entries(categories) as [string, CategoryScore][]).map(
                ([key, cat], i) => (
                  <div key={key} style={{ opacity: barsReady ? 1 : 0, transform: barsReady ? "translateY(0)" : "translateY(6px)", transition: `opacity 0.3s ${i * 60}ms, transform 0.3s ${i * 60}ms` }}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[13px] font-medium text-[var(--color-text)]">{cat.label}</span>
                        {ML_KEYS.has(key) && (
                          <span className="text-[9.5px] font-bold px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-600 ring-1 ring-violet-300/40 uppercase tracking-wide">ML</span>
                        )}
                        <span className="text-[10.5px] text-[var(--color-text-3)]">{cat.weight}%</span>
                      </div>
                      <span className={`text-[13px] font-bold tabular-nums ${scoreText(cat.score)}`}>
                        {cat.score}<span className="text-[10px] font-normal text-[var(--color-text-3)]">/100</span>
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barColor(cat.score)}`}
                        style={{ width: barsReady ? `${cat.score}%` : "0%", transition: `width 0.8s ease ${i * 60 + 200}ms` }}
                      />
                    </div>
                    <p className="text-[11.5px] text-[var(--color-text-3)] mt-0.5">{cat.description}</p>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="md:col-span-2 flex flex-col gap-3">
            <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[13px] font-semibold text-[var(--color-text)]">Keywords Found</p>
                <span className="text-[12px] font-bold text-emerald-500">{keyword_stats.matched_count} matched</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.values(bySection).flat().slice(0, 16).map((kw) => (
                  <span key={kw} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-300/40">
                    <CheckCircle2 className="w-2.5 h-2.5" />{kw}
                  </span>
                ))}
                {keyword_stats.matched_count > 16 && (
                  <span className="px-2 py-0.5 rounded-full text-[11px] text-[var(--color-text-3)]">
                    +{keyword_stats.matched_count - 16} more
                  </span>
                )}
              </div>
            </div>

            {(required_missing.length > 0 || preferred_missing.length > 0) && (
              <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[13px] font-semibold text-[var(--color-text)]">Missing Keywords</p>
                  <span className="text-[12px] font-bold text-red-500">{keyword_stats.missing_count} missing</span>
                </div>
                <div className="space-y-2">
                  {required_missing.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-red-500 font-semibold mb-1">Required</p>
                      <div className="flex flex-wrap gap-1.5">
                        {required_missing.map((kw) => (
                          <span key={kw} className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-500/10 text-red-600 ring-1 ring-red-300/40">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {preferred_missing.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-amber-600 font-semibold mb-1">Preferred</p>
                      <div className="flex flex-wrap gap-1.5">
                        {preferred_missing.map((kw) => (
                          <span key={kw} className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-700 ring-1 ring-amber-300/40">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── JD KEYWORDS BY SECTION ─────────────────────────────── */}
        {Object.keys(bySection).length > 0 && (
          <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-5">
            <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-1">
              JD Keywords by Resume Section
            </h2>
            <p className="text-[12px] text-[var(--color-text-3)] mb-5">
              How many job description keywords appear in each section of your resume — more is better
            </p>
            <div className="space-y-5">
              {Object.entries(bySection)
                .sort(([, a], [, b]) => b.length - a.length)
                .map(([sec, kws], i) => {
                  const maxKws = Math.max(...Object.values(bySection).map((k) => k.length));
                  const pct = Math.round((kws.length / Math.max(1, maxKws)) * 100);
                  return (
                    <div
                      key={sec}
                      style={{
                        opacity: barsReady ? 1 : 0,
                        transform: barsReady ? "translateY(0)" : "translateY(6px)",
                        transition: `opacity 0.3s ${i * 70}ms, transform 0.3s ${i * 70}ms`,
                      }}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[13.5px] font-semibold text-[var(--color-text)] capitalize">{sec}</span>
                        <span className="text-[12px] font-semibold text-[var(--color-text-3)] tabular-nums">
                          {kws.length} <span className="font-normal">keyword{kws.length !== 1 ? "s" : ""}</span>
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-500"
                          style={{ width: barsReady ? `${pct}%` : "0%", transition: `width 0.85s ease ${i * 70 + 150}ms` }}
                        />
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {kws.slice(0, 10).map((kw) => (
                          <span key={kw} className={`px-2 py-0.5 rounded-full text-[10.5px] font-medium ring-1 ${sectionPill(sec)}`}>{kw}</span>
                        ))}
                        {kws.length > 10 && (
                          <span className="text-[10.5px] text-[var(--color-text-3)] px-1 self-center">+{kws.length - 10} more</span>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* ── SYNONYM + WORD2VEC MATCHES ─────────────────────────── */}
        {(synonym_matches.length > 0 || word_semantic_matches.length > 0) && (
          <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-5">
            <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-1">
              Semantic & Synonym Matches
            </h2>
            <p className="text-[12px] text-[var(--color-text-3)] mb-4">
              Keywords matched via semantic similarity and alias expansion — these count toward your score even though the exact word isn&apos;t in your resume.
            </p>
            <div className="space-y-4">
              {synonym_matches.length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 mb-2">Synonym Matches</p>
                  <div className="flex flex-wrap gap-2">
                    {synonym_matches.map((s, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11.5px] ring-1 bg-amber-500/10 text-amber-700 ring-amber-300/40">
                        <span className="font-semibold">{s.matched_alias}</span>
                        <span className="text-amber-400">→</span>
                        <span>{s.keyword}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {word_semantic_matches.slice(0, 10).length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-violet-600 mb-2">Word Semantic Matches</p>
                  <div className="flex flex-wrap gap-2">
                    {word_semantic_matches.slice(0, 10).map((m, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11.5px] ring-1 bg-violet-500/10 text-violet-700 ring-violet-300/40">
                        <span className="font-semibold">{m.resume_term}</span>
                        <span className="text-violet-400">≈</span>
                        <span>{m.jd_term}</span>
                        <span className="font-bold text-[10px] text-violet-500">{Math.round(m.similarity * 100)}%</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── SENTENCE SEMANTIC MATCHES ──────────────────────────── */}
        {semantic_matches.length > 0 && (
          <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-4 h-4 text-indigo-500" />
              <h2 className="text-[15px] font-semibold text-[var(--color-text)]">
                Sentence-Level Semantic Matches
              </h2>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-600 ring-1 ring-indigo-300/40 uppercase tracking-wide ml-1">
                MiniLM
              </span>
            </div>
            <div className="space-y-3">
              {semantic_matches.slice(0, 5).map((m, i) => (
                <div key={i} className="rounded-xl bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] p-3">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-[10.5px] font-semibold text-[var(--color-text-3)] uppercase tracking-wide mb-0.5">JD requirement</p>
                      <p className="text-[12.5px] text-[var(--color-text)] line-clamp-2">{m.jd}</p>
                    </div>
                    <span className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      m.similarity >= 0.8 ? "bg-emerald-500/10 text-emerald-600" :
                      m.similarity >= 0.6 ? "bg-amber-500/10 text-amber-600" :
                      "bg-violet-500/10 text-violet-600"
                    }`}>
                      {Math.round(m.similarity * 100)}% match
                    </span>
                  </div>
                  <div className="h-px bg-[var(--color-border)] mb-2" />
                  <p className="text-[10.5px] font-semibold text-[var(--color-text-3)] uppercase tracking-wide mb-0.5">Your resume</p>
                  <p className="text-[12px] text-[var(--color-text-2)] line-clamp-2">{m.resume}</p>
                  <div className="mt-2 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-500" style={{ width: `${Math.round(m.similarity * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── AI REPORT ──────────────────────────────────────────── */}
        <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm p-5">
          <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-4">AI Report</h2>

          {fbLoading ? (
            <div className="flex items-center gap-2.5 text-[13px] text-[var(--color-text-3)] py-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating AI feedback…
            </div>
          ) : feedback ? (
            <div className="space-y-4">

              {/* Strengths + Weaknesses side by side — always compact */}
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="rounded-xl bg-emerald-500/5 ring-1 ring-emerald-300/30 p-4">
                  <div className="flex items-center gap-1.5 mb-3">
                    <ThumbsUp className="w-3.5 h-3.5 text-emerald-500" />
                    <p className="text-[11px] font-bold uppercase tracking-wide text-emerald-600">Strengths</p>
                  </div>
                  <ul className="space-y-2">
                    {feedback.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-[12.5px] text-[var(--color-text-2)]">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl bg-red-500/5 ring-1 ring-red-300/30 p-4">
                  <div className="flex items-center gap-1.5 mb-3">
                    <TrendingUp className="w-3.5 h-3.5 text-red-500" />
                    <p className="text-[11px] font-bold uppercase tracking-wide text-red-500">Weaknesses</p>
                  </div>
                  <ul className="space-y-2">
                    {feedback.weaknesses.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-[12.5px] text-[var(--color-text-2)]">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Suggestions — full width, each item as its own action card */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-500" />
                  <p className="text-[11px] font-bold uppercase tracking-wide text-blue-600">Suggestions</p>
                </div>
                <div className="space-y-2">
                  {feedback.suggestions.map((s, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-lg bg-blue-500/5 ring-1 ring-blue-300/30 px-4 py-3"
                    >
                      <span className="shrink-0 w-5 h-5 rounded-full bg-blue-500/15 text-blue-600 text-[11px] font-bold grid place-items-center mt-0.5">
                        {i + 1}
                      </span>
                      <p className="text-[13px] text-[var(--color-text-2)] leading-snug">{s}</p>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          ) : (
            <p className="text-[13px] text-[var(--color-text-3)]">AI feedback could not be generated.</p>
          )}
        </div>

        {/* ── AI RESUME TAILOR ────────────────────────────────────── */}
        {result && (result.required_missing.length > 0 || result.preferred_missing.length > 0) && (
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h2 className="text-[15px] font-semibold flex items-center gap-2 text-[var(--color-text)]">
                  <Wand2 className="w-4 h-4 text-indigo-500" />
                  AI Resume Tailor
                </h2>
                <p className="text-[12.5px] text-[var(--color-text-3)] mt-0.5">
                  AI rewrites specific bullets to incorporate your missing keywords.
                  Copy &amp; paste straight into your resume document.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {tailorOpen && !tailorLoading && (
                  <button
                    onClick={runTailor}
                    className="text-[12px] font-medium text-[var(--color-text-3)] hover:text-indigo-500 transition-colors"
                  >
                    Regenerate
                  </button>
                )}
                {!tailorOpen && (
                  <button
                    onClick={runTailor}
                    disabled={!result.resume_text}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13px] font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
                  >
                    <Wand2 className="w-3.5 h-3.5" />
                    Tailor my resume
                  </button>
                )}
              </div>
            </div>
            {tailorOpen && (
              <TailorPanel
                suggestions={tailorSuggestions}
                loading={tailorLoading}
                error={tailorError}
                resumeText={result.resume_text ?? ""}
                onRetry={runTailor}
              />
            )}
          </div>
        )}

        {/* ── BOTTOM CTA ─────────────────────────────────────────── */}
        <div className="text-center py-4">
          <button
            type="button"
            onClick={handleAnalyzeAnother}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[14px] font-semibold transition-colors shadow-sm"
          >
            Analyze Another Resume
          </button>
        </div>
      </div>
    </AppShell>
  );
}

/* ── stat card ────────────────────────────────────────────────────── */

function StatCard({
  label, value, sub, tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "green" | "red" | "amber" | "blue";
}) {
  const toneMap = {
    green: "bg-emerald-500/8  text-emerald-600",
    red:   "bg-red-500/8     text-red-600",
    amber: "bg-amber-500/8   text-amber-600",
    blue:  "bg-blue-500/8    text-blue-600",
  };
  return (
    <div className={`rounded-xl px-3 py-3 ${toneMap[tone]}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 mb-0.5">{label}</p>
      <p className="text-[20px] font-bold tabular-nums leading-none mb-0.5">{value}</p>
      <p className="text-[10.5px] opacity-70">{sub}</p>
    </div>
  );
}

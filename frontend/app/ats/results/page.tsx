"use client";

import {
  ArrowLeft, CheckCircle2, ChevronDown, ChevronUp,
  Lightbulb, Loader2, ThumbsUp, TrendingUp, Wand2, AlertTriangle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TailorPanel } from "@/components/ats/TailorPanel";
import type { ATSFeedback } from "@/lib/ats-api";
import { getAtsFeedback, tailorResume } from "@/lib/ats-api";
import type { AnalysisResult, CategoryScore, TailorSuggestion } from "@/types/ats";

/* ─── score accent (single colour that drives the whole page) ─── */
function accent(s: number) {
  if (s >= 80) return { hex: "#22c55e", cls: "text-emerald-500", bar: "bg-emerald-500", ring: "ring-emerald-500/30", pill: "bg-emerald-500/10 text-emerald-500" };
  if (s >= 65) return { hex: "#3b82f6", cls: "text-blue-500",    bar: "bg-blue-500",    ring: "ring-blue-500/30",    pill: "bg-blue-500/10    text-blue-500"   };
  if (s >= 50) return { hex: "#f59e0b", cls: "text-amber-600",   bar: "bg-amber-500",   ring: "ring-amber-500/30",   pill: "bg-amber-500/10   text-amber-600"  };
  return               { hex: "#ef4444", cls: "text-red-500",     bar: "bg-red-500",     ring: "ring-red-500/30",     pill: "bg-red-500/10     text-red-500"    };
}

function verdict(s: number) {
  if (s >= 80) return "Strong Match";
  if (s >= 65) return "Good Match";
  if (s >= 50) return "Fair Match";
  return "Needs Work";
}

function catColor(s: number) {
  if (s >= 70) return "bg-emerald-500";
  if (s >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function catText(s: number) {
  if (s >= 70) return "text-emerald-600";
  if (s >= 50) return "text-amber-600";
  return "text-red-500";
}

/* ─── category groups ─────────────────────────────────────────── */
const GROUPS = [
  { n: "01", label: "Keyword Match",   keys: ["keyword_match","required_coverage","context_quality","page_density"] },
  { n: "02", label: "Semantic & NLP",  keys: ["semantic_sentence","word_semantic","ontology_match"] },
  { n: "03", label: "Writing Quality", keys: ["achievement","bullet_quality","summary_quality","language_quality"] },
  { n: "04", label: "Career Profile",  keys: ["experience","education","title_match","career_health","certifications","skill_experience"] },
  { n: "05", label: "Format & ATS",    keys: ["parsability","structure","contact_completeness","readability"] },
];

export default function AtsResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [barsReady, setBarsReady] = useState(false);
  const [feedback, setFeedback] = useState<ATSFeedback | null>(null);
  const [fbLoading, setFbLoading] = useState(false);
  const [jdText, setJdText] = useState("");
  const [tailorOpen, setTailorOpen] = useState(false);
  const [tailorLoading, setTailorLoading] = useState(false);
  const [tailorSuggestions, setTailorSuggestions] = useState<TailorSuggestion[]>([]);
  const [tailorError, setTailorError] = useState<string | null>(null);
  const [expandBreakdown, setExpandBreakdown] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem("ats_result");
    if (!raw) { router.replace("/ats"); return; }
    try {
      const parsed = JSON.parse(raw) as AnalysisResult;
      setResult(parsed);
      setJdText(localStorage.getItem("ats_jd_text") ?? "");
      setHydrated(true);
      setTimeout(() => setBarsReady(true), 100);
      setFbLoading(true);
      getAtsFeedback(parsed).then(setFeedback).catch(() => setFeedback(null)).finally(() => setFbLoading(false));
    } catch { router.replace("/ats"); }
  }, [router]);

  if (!hydrated || !result) {
    return (
      <AppShell>
        <div className="min-h-[70dvh] grid place-items-center">
          <div className="h-8 w-8 rounded-full border-2 border-[var(--color-border)] border-t-indigo-500 animate-spin" />
        </div>
      </AppShell>
    );
  }

  const cats = result.categories as Record<string, CategoryScore>;
  const ac = accent(result.overall_score);
  const verd = verdict(result.overall_score);

  const requiredFound = result.jd_structure.required_count - result.required_missing.length;
  const preferredFound = result.jd_structure.preferred_count - result.preferred_missing.length;

  /* keywords by section */
  const bySection: Record<string, string[]> = {};
  for (const [kw, p] of Object.entries(result.keyword_placement)) {
    const s = p.section.toLowerCase();
    if (!bySection[s]) bySection[s] = [];
    bySection[s].push(kw);
  }

  function handleNew() { localStorage.removeItem("ats_result"); router.push("/ats"); }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-12">

        {/* ─── nav ──────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-8">
          <button onClick={handleNew} className="flex items-center gap-1.5 text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>
          <button onClick={handleNew} className="text-[12px] text-[var(--color-text-3)] border border-[var(--color-border)] px-3 py-1.5 rounded hover:bg-[var(--color-surface-2)] transition-colors">
            New scan
          </button>
        </div>

        {/* ─── 01 · SCORE HERO ──────────────────────────────── */}
        <section className="mb-10">
          <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)] mb-4">01 — Match Score</p>

          <div className="flex flex-col sm:flex-row gap-8 items-start">
            {/* Big number */}
            <div className="shrink-0">
              <div className="flex items-end gap-3 mb-3">
                <span className={`text-[80px] font-black leading-none tabular-nums ${ac.cls}`}
                  style={{ fontFeatureSettings: '"tnum"' }}>
                  {result.overall_score}
                </span>
                <div className="mb-3">
                  <span className="block text-[13px] text-[var(--color-text-3)] leading-none mb-1">/ 100</span>
                  <span className="block text-[22px] font-black text-[var(--color-text)] leading-none">{result.grade}</span>
                </div>
              </div>
              {/* Score bar */}
              <div className="w-[220px] h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${ac.bar}`}
                  style={{ width: barsReady ? `${result.overall_score}%` : "0%", transition: "width 1s cubic-bezier(.4,0,.2,1)" }} />
              </div>
              <p className={`text-[12px] font-semibold mt-2 ${ac.cls}`}>{verd}</p>
            </div>

            {/* Stat grid */}
            <div className="flex-1 grid grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)] rounded-xl overflow-hidden w-full">
              {[
                {
                  label: "Required Keywords",
                  value: `${requiredFound} / ${result.jd_structure.required_count}`,
                  sub: result.required_missing.length === 0 ? "All matched" : `${result.required_missing.length} missing`,
                  bad: result.required_missing.length > 0,
                },
                {
                  label: "Preferred Keywords",
                  value: `${preferredFound} / ${result.jd_structure.preferred_count}`,
                  sub: result.preferred_missing.length === 0 ? "All matched" : `${result.preferred_missing.length} missing`,
                  bad: false,
                },
                {
                  label: "Overall Coverage",
                  value: `${result.keyword_stats.match_percentage}%`,
                  sub: `${result.keyword_stats.matched_count} of ${result.keyword_stats.total_jd_keywords} keywords`,
                  bad: result.keyword_stats.match_percentage < 50,
                },
                {
                  label: "Experience",
                  value: `${result.experience_data.total_years} yrs`,
                  sub: result.experience_data.required_years
                    ? result.experience_data.total_years >= result.experience_data.required_years
                      ? "Meets requirement"
                      : `Requires ${result.experience_data.required_years}+ yrs`
                    : "No requirement stated",
                  bad: !!result.experience_data.required_years && result.experience_data.total_years < result.experience_data.required_years,
                },
              ].map(s => (
                <div key={s.label} className="bg-[var(--color-surface)] px-4 py-3.5">
                  <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-3)] font-semibold mb-1">{s.label}</p>
                  <p className={`text-[20px] font-black tabular-nums leading-none ${s.bad ? "text-red-500" : "text-[var(--color-text)]"}`}>{s.value}</p>
                  <p className={`text-[11px] mt-0.5 ${s.bad ? "text-red-500" : "text-[var(--color-text-3)]"}`}>{s.sub}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── 02 · KEYWORDS ────────────────────────────────── */}
        <section className="mb-10">
          <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)] mb-4">02 — Keywords</p>

          <div className="grid md:grid-cols-2 gap-5">
            {/* MISSING — left */}
            <div>
              {result.required_missing.length > 0 && (
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                    <span className="text-[11px] font-bold uppercase tracking-wider text-red-500">Required — Add these</span>
                    <span className="ml-auto text-[11px] font-bold text-red-500">{result.required_missing.length}</span>
                  </div>
                  <div className="space-y-1">
                    {result.required_missing.map((kw, i) => (
                      <div key={kw} className="flex items-center gap-3 px-3 py-2 border border-red-500/30 bg-red-500/10 rounded-lg group hover:border-red-500/40 transition-colors">
                        <span className="text-[10px] text-red-500/50 tabular-nums w-4">{String(i+1).padStart(2,"0")}</span>
                        <span className="text-[13px] font-medium text-[var(--color-text)] capitalize flex-1">{kw}</span>
                        <span className="text-[9px] font-black uppercase tracking-widest text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded">Required</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.preferred_missing.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                    <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600">Preferred — Nice to have</span>
                    <span className="ml-auto text-[11px] font-bold text-amber-600">{result.preferred_missing.length}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.preferred_missing.map(kw => (
                      <span key={kw} className="px-2.5 py-1 text-[11.5px] font-medium capitalize border border-amber-500/40 bg-amber-500/10 text-amber-600 rounded-full">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {result.required_missing.length === 0 && result.preferred_missing.length === 0 && (
                <div className="flex items-center gap-2 py-4">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span className="text-[13px] font-medium text-emerald-500">All keywords matched — great coverage!</span>
                </div>
              )}
            </div>

            {/* FOUND — right */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-500">Found in your resume</span>
                <span className="ml-auto text-[11px] font-bold text-emerald-500">{result.keyword_stats.matched_count}</span>
              </div>
              <div className="space-y-3">
                {Object.entries(bySection).sort(([,a],[,b]) => b.length - a.length).map(([sec, kws]) => (
                  <div key={sec}>
                    <p className="text-[9px] font-black uppercase tracking-[0.15em] text-[var(--color-text-3)] mb-1.5 capitalize">{sec}</p>
                    <div className="flex flex-wrap gap-1">
                      {kws.map(kw => (
                        <span key={kw} className="px-2 py-0.5 text-[11px] font-medium capitalize border border-emerald-500/30 bg-emerald-500/10 text-emerald-500 rounded">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ─── 03 · SCORE BREAKDOWN ─────────────────────────── */}
        <section className="mb-10">
          <button
            onClick={() => setExpandBreakdown(v => !v)}
            className="w-full flex items-center justify-between mb-4 group"
          >
            <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)]">03 — Score Breakdown</p>
            <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-3)] group-hover:text-[var(--color-text)] transition-colors">
              {expandBreakdown ? "Collapse" : "Expand all"} {expandBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          </button>

          <div className="border border-[var(--color-border)] rounded-xl overflow-hidden divide-y divide-[var(--color-border)]">
            {GROUPS.map((g, gi) => {
              const validKeys = g.keys.filter(k => cats[k]);
              if (!validKeys.length) return null;
              const avg = Math.round(validKeys.reduce((s, k) => s + cats[k].score, 0) / validKeys.length);
              const gc = accent(avg);
              return (
                <div key={g.n} className="bg-[var(--color-surface)]">
                  {/* Group row */}
                  <div className="flex items-center gap-4 px-5 py-3.5">
                    <span className="text-[10px] font-black text-[var(--color-text-3)] tabular-nums w-5 shrink-0">{g.n}</span>
                    <span className="text-[13px] font-semibold text-[var(--color-text)] flex-1">{g.label}</span>
                    <div className="w-32 h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden shrink-0">
                      <div className={`h-full rounded-full ${gc.bar}`}
                        style={{ width: barsReady ? `${avg}%` : "0%", transition: `width .7s ease ${gi * 80 + 200}ms` }} />
                    </div>
                    <span className={`text-[13px] font-bold tabular-nums w-7 text-right ${gc.cls}`}>{avg}</span>
                  </div>

                  {/* Expanded sub-rows */}
                  {expandBreakdown && (
                    <div className="border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
                      {validKeys.map((k, ki) => {
                        const cat = cats[k];
                        return (
                          <div key={k} className="flex items-center gap-4 px-5 py-2.5 border-b border-[var(--color-border)] last:border-0">
                            <span className="w-5 shrink-0" />
                            <span className="text-[12px] text-[var(--color-text-3)] flex-1">{cat.label}</span>
                            <div className="w-24 h-1 bg-[var(--color-border)] rounded-full overflow-hidden shrink-0">
                              <div className={`h-full rounded-full ${catColor(cat.score)}`}
                                style={{ width: barsReady ? `${cat.score}%` : "0%", transition: `width .6s ease ${gi * 80 + ki * 40 + 300}ms` }} />
                            </div>
                            <span className={`text-[12px] font-semibold tabular-nums w-7 text-right ${catText(cat.score)}`}>{cat.score}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── 04 · ACTIONS ─────────────────────────────────── */}
        {result.suggestions.length > 0 && (
          <section className="mb-10">
            <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)] mb-4">04 — Actions</p>
            <div className="space-y-2">
              {result.suggestions.slice(0, 6).map((s, i) => (
                <div key={i} className="flex items-start gap-4 px-4 py-3 border border-[var(--color-border)] rounded-lg bg-[var(--color-surface)] hover:border-[var(--color-text-3)] transition-colors">
                  <span className="text-[10px] font-black tabular-nums text-[var(--color-text-3)] w-4 shrink-0 mt-0.5">{String(i+1).padStart(2,"0")}</span>
                  <p className="text-[13px] text-[var(--color-text-2)] leading-snug">{s}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ─── 05 · AI REPORT ───────────────────────────────── */}
        <section className="mb-10">
          <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)] mb-4">05 — AI Report</p>

          {fbLoading ? (
            <div className="flex items-center gap-2 text-[13px] text-[var(--color-text-3)] py-4">
              <Loader2 className="w-4 h-4 animate-spin" /> Generating…
            </div>
          ) : feedback ? (
            <div className="grid sm:grid-cols-3 gap-px bg-[var(--color-border)] border border-[var(--color-border)] rounded-xl overflow-hidden">
              {[
                { icon: ThumbsUp, label: "Strengths", items: feedback.strengths, dot: "bg-emerald-500" },
                { icon: TrendingUp, label: "Weaknesses", items: feedback.weaknesses, dot: "bg-red-400" },
                { icon: Lightbulb, label: "Suggestions", items: feedback.suggestions, dot: "bg-indigo-400" },
              ].map(({ icon: Icon, label, items, dot }) => (
                <div key={label} className="bg-[var(--color-surface)] p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Icon className="w-3.5 h-3.5 text-[var(--color-text-3)]" />
                    <span className="text-[10px] font-black uppercase tracking-wider text-[var(--color-text-3)]">{label}</span>
                  </div>
                  <ul className="space-y-3">
                    {items.map((item, i) => (
                      <li key={i} className="flex items-start gap-2.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${dot} shrink-0 mt-1.5`} />
                        <span className="text-[12.5px] text-[var(--color-text-2)] leading-snug">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[13px] text-[var(--color-text-3)]">AI feedback unavailable.</p>
          )}
        </section>

        {/* ─── 06 · AI TAILOR ───────────────────────────────── */}
        {result && (result.required_missing.length > 0 || result.preferred_missing.length > 0) && (
          <section className="mb-10">
            <p className="text-[10px] tracking-[0.2em] uppercase font-bold text-[var(--color-text-3)] mb-4">06 — AI Resume Tailor</p>
            <div className="border border-[var(--color-border)] rounded-xl overflow-hidden bg-[var(--color-surface)]">
              <div className="flex items-center justify-between gap-4 px-5 py-4 border-b border-[var(--color-border)] flex-wrap">
                <div>
                  <p className="text-[13px] font-semibold text-[var(--color-text)]">Rewrite bullets to include missing keywords</p>
                  <p className="text-[11.5px] text-[var(--color-text-3)] mt-0.5">AI rewrites specific resume lines — copy straight into your document</p>
                </div>
                <div className="flex items-center gap-2">
                  {tailorOpen && !tailorLoading && (
                    <button onClick={runTailor} className="text-[12px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors">Regenerate</button>
                  )}
                  {!tailorOpen && (
                    <button onClick={runTailor} disabled={!result.resume_text}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[13px] font-semibold disabled:opacity-40 transition-colors">
                      <Wand2 className="w-3.5 h-3.5" /> Tailor resume
                    </button>
                  )}
                </div>
              </div>
              {tailorOpen && (
                <div className="p-5">
                  <TailorPanel suggestions={tailorSuggestions} loading={tailorLoading} error={tailorError} resumeText={result.resume_text ?? ""} onRetry={runTailor} />
                </div>
              )}
            </div>
          </section>
        )}

        {/* ─── bottom ───────────────────────────────────────── */}
        <div className="text-center">
          <button onClick={handleNew} className="px-6 py-2.5 rounded-lg border border-[var(--color-border)] text-[13px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors">
            ← Analyze another resume
          </button>
        </div>

      </div>
    </AppShell>
  );

  async function runTailor() {
    if (!result) return;
    setTailorOpen(true); setTailorLoading(true); setTailorError(null); setTailorSuggestions([]);
    try {
      const res = await tailorResume({ resume_text: result.resume_text ?? "", jd_text: jdText, required_missing: result.required_missing, preferred_missing: result.preferred_missing });
      setTailorSuggestions(res.suggestions);
    } catch (e) { setTailorError(e instanceof Error ? e.message : "Failed"); }
    finally { setTailorLoading(false); }
  }
}

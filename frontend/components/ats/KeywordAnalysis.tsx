"use client";

import type { AnalysisResult } from "@/types/ats";

interface Props {
  result: AnalysisResult;
}

const SECTION_WEIGHT: Record<string, { label: string; weight: string; pill: string }> = {
  skills: { label: "Skills", weight: "2.5×", pill: "bg-emerald-500/15 text-emerald-700 ring-emerald-300/50" },
  experience: { label: "Experience", weight: "1.5×", pill: "bg-emerald-400/10 text-emerald-600 ring-emerald-200/50" },
  summary: { label: "Summary", weight: "1.2×", pill: "bg-emerald-300/10 text-emerald-600 ring-emerald-200/40" },
};

function sectionStyle(section: string) {
  const key = section.toLowerCase();
  return SECTION_WEIGHT[key] ?? { label: section, weight: "1×", pill: "bg-[var(--color-surface-2)] text-[var(--color-text-2)] ring-[var(--color-border)]" };
}

export function KeywordAnalysis({ result }: Props) {
  const { keyword_placement, required_missing, preferred_missing, synonym_matches, word_semantic_matches, semantic_matches } = result;

  const bySection: Record<string, string[]> = {};
  for (const [kw, placement] of Object.entries(keyword_placement)) {
    const sec = placement.section.toLowerCase();
    if (!bySection[sec]) bySection[sec] = [];
    bySection[sec].push(kw);
  }

  const topSemantic = semantic_matches.slice(0, 5);
  const topWord = word_semantic_matches.slice(0, 8);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-3">
            Matched Keywords
            <span className="ml-2 text-[12px] font-normal text-emerald-500">
              {Object.values(bySection).flat().length} matched
            </span>
          </h3>
          {Object.keys(bySection).length === 0 ? (
            <p className="text-[13px] text-[var(--color-text-3)]">No keywords matched.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(bySection).map(([sec, keywords]) => {
                const style = sectionStyle(sec);
                return (
                  <div key={sec}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider">
                        {style.label}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-3)]">{style.weight}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {keywords.map((kw) => (
                        <span
                          key={kw}
                          className={`text-[12px] px-2 py-0.5 rounded-full ring-1 ${style.pill}`}
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-3">
            Missing Keywords
            <span className="ml-2 text-[12px] font-normal text-red-500">
              {(required_missing.length + preferred_missing.length)} missing
            </span>
          </h3>
          {required_missing.length === 0 && preferred_missing.length === 0 ? (
            <p className="text-[13px] text-emerald-500 font-medium">All keywords matched!</p>
          ) : (
            <div className="space-y-3">
              {required_missing.length > 0 && (
                <div>
                  <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-1.5">
                    Required ({required_missing.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {required_missing.map((kw) => (
                      <span
                        key={kw}
                        className="text-[12px] px-2 py-0.5 rounded-full ring-1 bg-red-500/10 text-red-600 ring-red-300/50"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {preferred_missing.length > 0 && (
                <div>
                  <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-1.5">
                    Preferred ({preferred_missing.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {preferred_missing.map((kw) => (
                      <span
                        key={kw}
                        className="text-[12px] px-2 py-0.5 rounded-full ring-1 bg-amber-500/10 text-amber-600 ring-amber-300/50"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {synonym_matches.length > 0 && (
        <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-3">
            Synonym Matches
            <span className="ml-2 text-[11px] font-normal text-[var(--color-text-3)]">
              keywords matched via alias expansion
            </span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {synonym_matches.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[12px] px-2.5 py-1 rounded-full ring-1 bg-amber-500/10 text-amber-700 ring-amber-300/50"
              >
                <span className="font-medium">{s.matched_alias}</span>
                <span className="text-amber-500/70">→</span>
                <span className="text-[11px] opacity-80">{s.keyword}</span>
                <span className="text-[10px] text-amber-500/70 ml-0.5">Synonym</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {topWord.length > 0 && (
        <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-3">
            Word Semantic Matches
            <span className="ml-2 text-[11px] font-normal text-[var(--color-text-3)]">
              Word2Vec similarities
            </span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {topWord.map((m, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-[12px] px-2.5 py-1 rounded-full ring-1 bg-violet-500/10 text-violet-700 ring-violet-300/50"
              >
                <span className="font-medium">{m.resume_term}</span>
                <span className="text-violet-400">≈</span>
                <span>{m.jd_term}</span>
                <span className="text-[10px] text-violet-500 font-semibold">
                  {Math.round(m.similarity * 100)}%
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {topSemantic.length > 0 && (
        <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-3">
            Sentence Semantic Matches
            <span className="ml-2 text-[11px] font-normal text-[var(--color-text-3)]">
              MiniLM sentence-level similarity
            </span>
          </h3>
          <div className="space-y-3">
            {topSemantic.map((m, i) => (
              <div
                key={i}
                className="rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] p-3"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-0.5">
                      JD
                    </p>
                    <p className="text-[12px] text-[var(--color-text)] line-clamp-2">{m.jd}</p>
                  </div>
                  <span
                    className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      m.similarity >= 0.8
                        ? "bg-emerald-500/10 text-emerald-600"
                        : m.similarity >= 0.6
                        ? "bg-amber-500/10 text-amber-600"
                        : "bg-violet-500/10 text-violet-600"
                    }`}
                  >
                    {Math.round(m.similarity * 100)}%
                  </span>
                </div>
                <div className="h-px bg-[var(--color-border)] mb-2" />
                <div>
                  <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-0.5">
                    Resume
                  </p>
                  <p className="text-[12px] text-[var(--color-text-2)] line-clamp-2">{m.resume}</p>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet-500"
                    style={{ width: `${Math.round(m.similarity * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

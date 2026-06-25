"use client";

import { CheckCircle2, FileText, ScanText, Sparkles, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { analyzeResume } from "@/lib/ats-api";

/* ── keyword extraction (animation only) ─────────────────────────── */

const STOP = new Set([
  "the","and","or","to","of","a","an","in","for","with","is","are","be",
  "have","will","you","your","we","our","that","this","as","at","by","on",
  "from","not","but","if","it","its","any","all","can","has","was","were",
  "been","being","do","does","did","so","such","than","their","they","them",
  "these","those","up","into","about","through","between","both","well",
  "more","most","other","also","when","who","how","what","which","use",
  "using","used","work","working","must","should","able","good","strong",
  "team","role","position","job","candidate","experience","years","least",
  "including","related","skills","requirements","responsibilities","etc",
  "will","may","including","minimum","ability","knowledge","excellent",
]);

function extractAnimationKeywords(text: string): string[] {
  const words = text
    .split(/[\s,;:()\[\]\/\\|•\-–—"']+/)
    .map((w) => w.replace(/[^a-zA-Z0-9+#.]/g, "").trim())
    .filter((w) => w.length >= 3 && !STOP.has(w.toLowerCase()));
  const seen = new Set<string>();
  const out: string[] = [];
  for (const w of words) {
    if (!seen.has(w.toLowerCase()) && out.length < 24) {
      seen.add(w.toLowerCase());
      out.push(w);
    }
  }
  return out;
}

/* ── constants ────────────────────────────────────────────────────── */

const LOADING_STEPS = [
  "Extracting text from document…",
  "Parsing resume sections…",
  "Parsing job description…",
  "Extracting keywords…",
  "Matching required skills…",
  "Expanding skill synonyms…",
  "Running semantic comparison…",
  "Matching sentence context…",
  "Calculating experience years…",
  "Checking ATS compatibility…",
  "Computing final score…",
];

const KW_COLORS = [
  "bg-indigo-500/10 text-indigo-400 ring-indigo-400/30",
  "bg-emerald-500/10 text-emerald-400 ring-emerald-400/30",
  "bg-violet-500/10 text-violet-400 ring-violet-400/30",
  "bg-amber-500/10 text-amber-400 ring-amber-400/30",
  "bg-blue-500/10 text-blue-400 ring-blue-400/30",
  "bg-rose-500/10 text-rose-400 ring-rose-400/30",
  "bg-teal-500/10 text-teal-400 ring-teal-400/30",
  "bg-sky-500/10 text-sky-400 ring-sky-400/30",
];

const POSITIONS = [
  { left: "6%",  top: "8%"  }, { left: "28%", top: "6%"  }, { left: "55%", top: "10%" },
  { left: "75%", top: "5%"  }, { left: "88%", top: "18%" }, { left: "15%", top: "28%" },
  { left: "42%", top: "25%" }, { left: "68%", top: "30%" }, { left: "82%", top: "42%" },
  { left: "3%",  top: "48%" }, { left: "25%", top: "52%" }, { left: "50%", top: "50%" },
  { left: "72%", top: "58%" }, { left: "88%", top: "65%" }, { left: "10%", top: "70%" },
  { left: "35%", top: "72%" }, { left: "58%", top: "74%" }, { left: "78%", top: "78%" },
  { left: "2%",  top: "82%" }, { left: "20%", top: "86%" }, { left: "48%", top: "88%" },
  { left: "65%", top: "90%" }, { left: "82%", top: "86%" }, { left: "92%", top: "92%" },
];

type Step = "resume" | "jd" | "analyzing";
type Tab  = "upload" | "paste";

/* ── page ─────────────────────────────────────────────────────────── */

export default function AtsPage() {
  const router = useRouter();

  const [step, setStep] = useState<Step>("resume");
  const [tab,  setTab]  = useState<Tab>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [jd,   setJd]   = useState("");
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loadingStep, setLoadingStep] = useState(0);
  const [keywords, setKeywords]       = useState<string[]>([]);
  const [shown, setShown]             = useState<number>(0);

  const hasResume = tab === "upload" ? !!file : resumeText.trim().length >= 50;

  const handleFile = useCallback((f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      setError("Please upload a .pdf or .docx file.");
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  function goToJD() {
    if (!hasResume) {
      setError(
        tab === "upload"
          ? "Please upload a PDF or DOCX resume."
          : "Please paste at least 50 characters of your resume text.",
      );
      return;
    }
    setError(null);
    setStep("jd");
  }

  async function analyze() {
    if (!jd.trim()) {
      setError("Please paste the job description.");
      return;
    }
    setError(null);

    const kws = extractAnimationKeywords(jd);
    setKeywords(kws);
    setShown(0);
    setLoadingStep(0);
    setStep("analyzing");

    kws.forEach((_, i) => {
      setTimeout(() => setShown(i + 1), 150 + i * 220);
    });

    let s = 0;
    const stepTimer = setInterval(() => {
      s++;
      setLoadingStep(s);
      if (s >= LOADING_STEPS.length - 1) clearInterval(stepTimer);
    }, 600);

    const fd = new FormData();
    fd.append("job_description", jd);
    if (tab === "upload" && file) fd.append("file", file);
    else fd.append("resume_text", resumeText);

    try {
      const result = await analyzeResume(fd);
      clearInterval(stepTimer);
      sessionStorage.setItem("ats_result", JSON.stringify(result));
      sessionStorage.setItem("ats_jd_text", jd);
      router.push("/ats/results");
    } catch (err) {
      clearInterval(stepTimer);
      setStep("jd");
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    }
  }

  const jdCharCount  = jd.length;
  const hasRequired  = /required|must.have|minimum/i.test(jd);
  const hasPreferred = /preferred|nice.to.have|bonus|plus/i.test(jd);

  /* ── ANALYZING screen ─────────────────────────────────────────── */

  if (step === "analyzing") {
    const progress = Math.min(((loadingStep + 1) / LOADING_STEPS.length) * 100, 100);
    return (
      <AppShell>
        <div
          className="min-h-[82dvh] flex flex-col items-center justify-center px-6 select-none relative overflow-hidden"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.12) 0%, transparent 60%)",
          }}
        >
          <p className="text-[11px] font-bold text-indigo-500 uppercase tracking-[0.2em] mb-2">
            Analyzing your resume
          </p>
          <p className="text-[28px] sm:text-[34px] font-bold text-[var(--color-text)] mb-10 text-center">
            Extracting keywords from JD…
          </p>

          <div className="relative w-full max-w-2xl h-72 mb-12">
            {keywords.map((kw, i) => {
              const pos     = POSITIONS[i] ?? { left: "50%", top: "50%" };
              const visible = i < shown;
              return (
                <span
                  key={kw}
                  className={`absolute px-2.5 py-1 rounded-full text-[12.5px] font-semibold ring-1 ${KW_COLORS[i % KW_COLORS.length]}`}
                  style={{
                    left: pos.left,
                    top: pos.top,
                    opacity: visible ? 1 : 0,
                    transform: visible ? "scale(1) translateY(0)" : "scale(0.5) translateY(8px)",
                    transition: "opacity 0.4s ease, transform 0.4s ease",
                    pointerEvents: "none",
                  }}
                >
                  {kw}
                </span>
              );
            })}
          </div>

          <div className="w-full max-w-sm">
            <div className="h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden mb-3">
              <div
                className="h-full rounded-full bg-indigo-600 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-center text-[13px] text-[var(--color-text-3)] animate-pulse">
              {LOADING_STEPS[Math.min(loadingStep, LOADING_STEPS.length - 1)]}
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  /* ── STEP 1 + 2 ───────────────────────────────────────────────── */

  return (
    <AppShell>
      <div className="flex flex-col min-h-[calc(100vh-56px)]">

        {/* ── Hero ── */}
        <div className="relative overflow-hidden shrink-0">
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-600/15 via-indigo-600/4 to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(99,102,241,0.12),transparent)] pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_55%_40%_at_90%_15%,rgba(139,92,246,0.08),transparent)] pointer-events-none" />
          <div className="relative text-center px-6 pt-12 pb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-500/40 mb-5">
              <ScanText className="w-8 h-8 text-white" />
            </div>

            {step === "resume" ? (
              <>
                <h1 className="text-3xl font-bold tracking-tight">ATS Resume Scanner</h1>
                <p className="text-[var(--color-text-2)] mt-2 text-sm max-w-xs mx-auto leading-relaxed">
                  See exactly how your resume scores against a job — keyword gaps, skill misses, actionable fixes.
                </p>
                <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                  {["Know before you apply", "Spot every missing keyword", "Fix what's filtering you out"].map((f) => (
                    <span key={f} className="inline-flex items-center gap-1 text-[11.5px] font-medium px-2.5 py-1 rounded-full bg-[var(--color-surface)]/60 ring-1 ring-[var(--color-border)] text-[var(--color-text-2)]">
                      <Sparkles className="w-3 h-3 text-indigo-400" />
                      {f}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <>
                <h1 className="text-3xl font-bold tracking-tight">Add the job description</h1>
                <p className="text-[var(--color-text-2)] mt-2 text-sm max-w-xs mx-auto leading-relaxed">
                  More text = more keywords detected = better analysis.
                </p>
              </>
            )}
          </div>
        </div>

        {/* ── Form ── */}
        <div className="flex-1 max-w-2xl w-full mx-auto px-4 sm:px-6 py-8">

          {/* ── step indicator ──────────────────────────────────── */}
          <div className="flex items-center gap-3 mb-6">
            <StepDot n={1} active={step === "resume"} done={step === "jd"} label="Upload Resume" />
            {step === "jd" && (
              <>
                <div className="flex-1 h-0.5 rounded-full bg-indigo-500" />
                <StepDot n={2} active done={false} label="Job Description" />
              </>
            )}
          </div>

          {error && (
            <div className="mb-4 rounded-xl bg-red-500/10 ring-1 ring-red-400/30 px-4 py-3">
              <p className="text-[13px] text-red-500">{error}</p>
            </div>
          )}

          {/* ── STEP 1: RESUME ──────────────────────────────────── */}
          {step === "resume" && (
            <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-xl shadow-black/5 overflow-hidden">

              {/* Tab switcher */}
              <div className="flex border-b border-[var(--color-border)]">
                {(["upload", "paste"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => { setTab(t); setError(null); }}
                    className={`flex-1 py-3 text-[13px] font-semibold transition-colors ${
                      tab === t
                        ? "text-indigo-600 border-b-2 border-indigo-600 bg-indigo-500/5"
                        : "text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)]"
                    }`}
                  >
                    {t === "upload" ? "Upload File" : "Paste Text"}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {tab === "upload" ? (
                  <>
                    {/* Drop zone */}
                    <div
                      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                      onDragLeave={() => setDragging(false)}
                      onDrop={onDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`cursor-pointer rounded-2xl border-2 border-dashed py-14 px-6 text-center transition-all duration-200 ${
                        dragging
                          ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
                          : file
                          ? "border-emerald-500/50 bg-emerald-500/5"
                          : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-indigo-400/60 hover:bg-indigo-500/5"
                      }`}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx"
                        className="hidden"
                        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                      />
                      {file ? (
                        <div className="flex flex-col items-center">
                          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 ring-1 ring-emerald-400/40 flex items-center justify-center mb-3">
                            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                          </div>
                          <p className="text-[15px] font-semibold text-[var(--color-text)]">{file.name}</p>
                          <p className="text-[12.5px] text-[var(--color-text-3)] mt-1">
                            {(file.size / 1024).toFixed(1)} KB · click to change
                          </p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center">
                          {/* Document illustration */}
                          <div className="relative mb-4">
                            <div className="w-14 h-14 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-sm flex items-center justify-center">
                              <FileText className="w-7 h-7 text-indigo-500" />
                            </div>
                            <div className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center shadow-sm">
                              <Upload className="w-2.5 h-2.5 text-white" />
                            </div>
                          </div>
                          <p className="text-[16px] font-semibold text-[var(--color-text)]">
                            Drop your resume here
                          </p>
                          <p className="text-[13px] text-[var(--color-text-3)] mt-1 mb-4">
                            or click to browse your files
                          </p>
                          {/* Format badges */}
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-1 rounded-lg bg-red-500/10 text-red-600 text-[11.5px] font-bold ring-1 ring-red-300/40">
                              PDF
                            </span>
                            <span className="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-600 text-[11.5px] font-bold ring-1 ring-blue-300/40">
                              DOCX
                            </span>
                            <span className="text-[11px] text-[var(--color-text-3)]">· up to 10 MB</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div>
                    <p className="text-[12px] text-[var(--color-text-3)] mb-2">Paste your resume text below (plain text)</p>
                    <textarea
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                      placeholder="Paste your resume here…"
                      rows={14}
                      className="w-full rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[12.5px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 resize-none font-mono"
                    />
                    {resumeText.length > 0 && (
                      <p className="text-[11px] text-[var(--color-text-3)] mt-1.5 text-right tabular-nums">
                        {resumeText.length.toLocaleString()} chars
                        {resumeText.trim().length < 50 && (
                          <span className="text-amber-500 ml-2">· need at least 50</span>
                        )}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="px-6 pb-6 flex justify-end">
                <button
                  type="button"
                  onClick={goToJD}
                  className="inline-flex items-center gap-2 px-7 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[14px] font-semibold shadow-sm shadow-indigo-500/30 transition-colors"
                >
                  Continue
                  <span aria-hidden>→</span>
                </button>
              </div>
            </div>
          )}

          {/* ── STEP 2: JD ──────────────────────────────────────── */}
          {step === "jd" && (
            <div className="space-y-3">
              {/* Resume confirmed chip */}
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[var(--color-surface)] ring-1 ring-emerald-400/40 shadow-sm">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-[13px] font-semibold text-[var(--color-text)] truncate">
                    {tab === "upload" ? file?.name : "Resume text ready"}
                  </p>
                  <p className="text-[11px] text-[var(--color-text-3)]">
                    {tab === "upload"
                      ? `${((file?.size ?? 0) / 1024).toFixed(1)} KB`
                      : `${resumeText.length.toLocaleString()} characters`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => { setStep("resume"); setError(null); }}
                  className="ml-auto shrink-0 text-[12px] text-indigo-500 hover:text-indigo-600 hover:underline transition-colors"
                >
                  Change
                </button>
              </div>

              <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-xl shadow-black/5 overflow-hidden">
                <div className="px-6 pt-6 pb-4">
                  <textarea
                    value={jd}
                    onChange={(e) => setJd(e.target.value)}
                    placeholder="Paste the full job description here — include requirements, responsibilities, and qualifications for the best analysis…"
                    rows={16}
                    autoFocus
                    className="w-full rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 resize-none"
                  />
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    {hasRequired && (
                      <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 ring-1 ring-emerald-300/40 font-medium">
                        ✓ Required keywords detected
                      </span>
                    )}
                    {hasPreferred && (
                      <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 ring-1 ring-amber-300/40 font-medium">
                        ✓ Preferred keywords detected
                      </span>
                    )}
                    {jdCharCount > 0 && (
                      <span className="text-[11px] text-[var(--color-text-3)] ml-auto tabular-nums">
                        {jdCharCount.toLocaleString()} chars
                      </span>
                    )}
                  </div>
                </div>

                <div className="px-6 pb-6 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
                  <button
                    type="button"
                    onClick={() => { setStep("resume"); setError(null); }}
                    className="text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={analyze}
                    className="inline-flex items-center gap-2 px-7 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[14px] font-semibold shadow-sm shadow-indigo-500/30 transition-colors"
                  >
                    <ScanText className="w-4 h-4" />
                    Analyze Resume
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

/* ── StepDot ──────────────────────────────────────────────────────── */

function StepDot({
  n,
  active,
  done,
  label,
}: {
  n: number;
  active: boolean;
  done: boolean;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`w-7 h-7 rounded-full grid place-items-center text-[12px] font-bold shrink-0 transition-all duration-300 ${
          done
            ? "bg-emerald-500 text-white shadow-sm shadow-emerald-500/30"
            : active
            ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30"
            : "bg-[var(--color-surface-2)] text-[var(--color-text-3)] ring-1 ring-[var(--color-border)]"
        }`}
      >
        {done ? "✓" : n}
      </span>
      <span
        className={`text-[13px] font-medium hidden sm:block transition-colors ${
          active ? "text-[var(--color-text)]" : "text-[var(--color-text-3)]"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

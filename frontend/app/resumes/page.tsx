"use client";
import { useState } from "react";
import { Plus, FileText, TrendingUp, Zap, BarChart3 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ResumeCard } from "@/components/resumes/ResumeCard";
import { UploadResumeModal } from "@/components/resumes/UploadResumeModal";
import { SkillGapPanel } from "@/components/resumes/SkillGapPanel";
import { useResumes } from "@/hooks/useResumes";

const HOW_IT_WORKS = [
  { icon: FileText, color: "bg-indigo-500/10 text-indigo-400", title: "Upload per role", desc: "Add a resume for each track — Java, Python, AI. Tag it with the target role." },
  { icon: TrendingUp, color: "bg-violet-500/10 text-violet-400", title: "Auto-matches your JDs", desc: "We scan all your job applications for that role and extract what skills they ask for." },
  { icon: BarChart3, color: "bg-emerald-500/10 text-emerald-400", title: "See what's missing", desc: "Skills ranked into Critical / High / Medium — see the full picture at a glance." },
];

export default function ResumesPage() {
  const { data: resumes = [], isLoading } = useResumes();
  const [showUpload, setShowUpload] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selectedResume = resumes.find(r => r.id === selectedId);

  return (
    <AppShell>
      <div className="flex flex-col min-h-[calc(100vh-56px)]">

        {/* ── Hero ── */}
        <div className="relative overflow-hidden shrink-0">
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-600/15 via-indigo-600/4 to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(99,102,241,0.12),transparent)] pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_55%_40%_at_90%_15%,rgba(139,92,246,0.08),transparent)] pointer-events-none" />
          <div className="absolute top-6 left-[12%] w-24 h-24 rounded-full bg-indigo-500/5 blur-2xl pointer-events-none" />
          <div className="absolute top-4 right-[15%] w-32 h-32 rounded-full bg-violet-500/6 blur-3xl pointer-events-none" />

          <div className="relative text-center px-6 pt-12 pb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-500/40 mb-5">
              <TrendingUp className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Skill Gap Analyzer</h1>
            <p className="text-[var(--color-text-2)] mt-2 text-sm max-w-sm mx-auto leading-relaxed">
              Upload role-specific resumes. See which skills your target jobs demand that you haven&apos;t listed yet.
            </p>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
              {[
                { icon: FileText, label: "Per-role resume tracking" },
                { icon: Zap, label: "Based on your actual JDs" },
                { icon: BarChart3, label: "Ranked by job frequency" },
              ].map(({ icon: Icon, label }) => (
                <span key={label} className="inline-flex items-center gap-1.5 text-[11.5px] font-medium px-3 py-1.5 rounded-full bg-[var(--color-surface)]/60 ring-1 ring-[var(--color-border)] text-[var(--color-text-2)]">
                  <Icon className="w-3 h-3 text-indigo-400" />
                  {label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ── Content ── */}
        <div className="flex-1 max-w-[1100px] w-full mx-auto px-6 py-8">

          {isLoading && (
            <div className="flex gap-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-28 flex-1 rounded-2xl bg-[var(--color-border)] animate-pulse opacity-40" />
              ))}
            </div>
          )}

          {/* ── Empty state ── */}
          {!isLoading && resumes.length === 0 && (
            <div className="space-y-10">
              <div className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 via-[var(--color-surface)] to-violet-500/5 p-8 text-center shadow-xl shadow-indigo-500/5">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-px bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent" />
                <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 ring-1 ring-indigo-500/20 flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-indigo-400" />
                </div>
                <h2 className="text-xl font-bold mb-2">Start with your first resume</h2>
                <p className="text-[13.5px] text-[var(--color-text-3)] max-w-sm mx-auto mb-6 leading-relaxed">
                  Upload your Java, Python, or AI resume and we&apos;ll automatically match it against your job applications to find skill gaps.
                </p>
                <Button onClick={() => setShowUpload(true)} className="gap-2 mx-auto">
                  <Plus className="w-4 h-4" />
                  Upload your first resume
                </Button>
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--color-text-3)] mb-4 text-center">How it works</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {HOW_IT_WORKS.map((step, i) => (
                    <div key={step.title} className="relative rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
                      <div className="absolute top-4 right-4 text-[11px] font-bold text-[var(--color-text-3)] opacity-40">{String(i + 1).padStart(2, "0")}</div>
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${step.color}`}>
                        <step.icon className="w-4 h-4" />
                      </div>
                      <p className="text-[13px] font-semibold mb-1">{step.title}</p>
                      <p className="text-[12px] text-[var(--color-text-3)] leading-relaxed">{step.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Resume list (no selection) ── */}
          {resumes.length > 0 && selectedId === null && (
            <>
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--color-text-3)]">Your Resumes</span>
                  <span className="text-[10px] bg-indigo-500/10 text-indigo-400 font-bold px-1.5 py-0.5 rounded-full">{resumes.length}</span>
                </div>
                <Button onClick={() => setShowUpload(true)} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Upload Resume
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {resumes.map(r => (
                  <ResumeCard
                    key={r.id}
                    resume={r}
                    isSelected={false}
                    onSelect={() => setSelectedId(r.id)}
                  />
                ))}
              </div>
            </>
          )}

          {/* ── Full-width gap result ── */}
          {resumes.length > 0 && selectedId !== null && selectedResume && (
            <SkillGapPanel
              resumeId={selectedId}
              resumeName={selectedResume.name}
              roleTag={selectedResume.role_tag}
              onBack={() => setSelectedId(null)}
            />
          )}
        </div>
      </div>

      {showUpload && <UploadResumeModal onClose={() => setShowUpload(false)} />}
    </AppShell>
  );
}

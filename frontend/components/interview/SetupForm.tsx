"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Layers,
  Loader2,
  Mic,
  Users,
} from "lucide-react";

import { useStartAgentSession, useStartSession } from "@/hooks/useInterview";

// ─── Data ─────────────────────────────────────────────────────────────────────

const INTERVIEW_TYPES = [
  {
    label: "HR Behavioral",
    icon: Users,
    desc: "STAR situations, teamwork & conflict",
  },
  {
    label: "System Design",
    icon: Layers,
    desc: "Architecture, scalability & trade-offs",
  },
  {
    label: "JD Based",
    icon: FileText,
    desc: "From a job description you paste",
  },
] as const;

const TECH_CHIPS = [
  "Java", "Python", "Spring Boot", "FastAPI", "React", "Agentic AI", "Microservices",
];

const DIFFICULTIES = [
  {
    key: "easy" as const,
    emoji: "🌱",
    label: "Easy",
    desc: "Core concepts & common patterns",
    activeBorder: "border-emerald-500",
    activeBg: "bg-emerald-500/8",
    activeText: "text-emerald-500",
    activeBar: "bg-emerald-500",
  },
  {
    key: "medium" as const,
    emoji: "⚡",
    label: "Medium",
    desc: "Real-world scenarios & trade-offs",
    activeBorder: "border-amber-500",
    activeBg: "bg-amber-500/8",
    activeText: "text-amber-500",
    activeBar: "bg-amber-500",
  },
  {
    key: "hard" as const,
    emoji: "🔥",
    label: "Hard",
    desc: "Deep internals, edge cases & scale",
    activeBorder: "border-red-500",
    activeBg: "bg-red-500/8",
    activeText: "text-red-500",
    activeBar: "bg-red-500",
  },
] as const;

const QUESTION_COUNTS = [3, 5, 7, 10, 12, 15];

const ROLES = [
  "Software Engineer", "Frontend Engineer", "Backend Engineer",
  "Full Stack Engineer", "Data Engineer", "DevOps Engineer", "ML / AI Engineer",
];

const EXP_OPTIONS = ["0–1", "1–3", "3–5", "5–10", "10+"];

// ─── Components ───────────────────────────────────────────────────────────────

function SectionHeading({
  step,
  title,
  subtitle,
}: {
  step: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-start gap-4 mb-5">
      <span className="shrink-0 w-7 h-7 rounded-full bg-indigo-500/15 text-indigo-500 text-xs font-bold flex items-center justify-center mt-0.5">
        {step}
      </span>
      <div>
        <h3 className="font-semibold text-[var(--color-text)]">{title}</h3>
        {subtitle && <p className="text-xs text-[var(--color-text-3)] mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function Divider() {
  return <div className="border-t border-[var(--color-border)] my-8" />;
}

function DotPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const idx = QUESTION_COUNTS.indexOf(value);

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={() => idx > 0 && onChange(QUESTION_COUNTS[idx - 1])}
        disabled={idx === 0}
        className="w-7 h-7 rounded-full border border-[var(--color-border)] flex items-center justify-center hover:border-indigo-400 hover:bg-indigo-500/5 disabled:opacity-20 disabled:cursor-not-allowed transition-all shrink-0"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
      </button>

      <div className="flex items-center gap-2">
        {QUESTION_COUNTS.map((count, i) => (
          <button
            key={count}
            onClick={() => onChange(count)}
            title={`${count} questions`}
            className={`rounded-full transition-all duration-200 ${
              i === idx
                ? "w-4 h-4 bg-indigo-500 shadow-[0_0_0_3px_rgba(99,102,241,0.15)]"
                : i < idx
                ? "w-3 h-3 bg-indigo-400/50"
                : "w-2.5 h-2.5 border-2 border-[var(--color-border)] hover:border-indigo-400"
            }`}
          />
        ))}
      </div>

      <button
        onClick={() => idx < QUESTION_COUNTS.length - 1 && onChange(QUESTION_COUNTS[idx + 1])}
        disabled={idx === QUESTION_COUNTS.length - 1}
        className="w-7 h-7 rounded-full border border-[var(--color-border)] flex items-center justify-center hover:border-indigo-400 hover:bg-indigo-500/5 disabled:opacity-20 disabled:cursor-not-allowed transition-all shrink-0"
      >
        <ChevronRight className="w-3.5 h-3.5" />
      </button>

      <span className="text-sm font-semibold tabular-nums text-[var(--color-text)]">
        {value} <span className="font-normal text-[var(--color-text-3)]">questions · ≈{Math.round(value * 4.5)} min</span>
      </span>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function SetupForm() {
  const router = useRouter();
  const { mutateAsync, isPending, error } = useStartSession();
  const { mutateAsync: mutateAgent, isPending: isAgentPending, error: agentError } = useStartAgentSession();

  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedTech, setSelectedTech] = useState<string | null>(null);
  const [customTopic, setCustomTopic] = useState("");
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");
  const [numQuestions, setNumQuestions] = useState(7);
  const [role, setRole] = useState(ROLES[0]);
  const [yearsExp, setYearsExp] = useState("1–3");
  const [jdText, setJdText] = useState("");
  const [useCustomQ, setUseCustomQ] = useState(false);
  const [customQText, setCustomQText] = useState("");
  const [agentMode, setAgentMode] = useState(false);

  const resolvedTopic = customTopic.trim() || selectedTech || selectedType || "";
  const parsedCustomQ = customQText
    .split("\n")
    .map((q) => q.trim())
    .filter((q) => q.length > 0);

  function pickType(label: string) {
    setSelectedType(label === selectedType ? null : label);
    setSelectedTech(null);
    setCustomTopic("");
  }

  function pickTech(chip: string) {
    setSelectedTech(chip === selectedTech ? null : chip);
    setSelectedType(null);
    setCustomTopic("");
  }

  function onCustomChange(val: string) {
    setCustomTopic(val);
    if (val.trim()) {
      setSelectedType(null);
      setSelectedTech(null);
    }
  }

  const isJdBased = selectedType === "JD Based";
  const anyPending = isPending || isAgentPending;
  const canStart = !anyPending && (
    useCustomQ
      ? parsedCustomQ.length >= 1
      : resolvedTopic.trim().length > 0 && (!isJdBased || jdText.trim().length > 0)
  );

  async function handleStart() {
    if (!canStart) return;

    if (agentMode && !useCustomQ) {
      const res = await mutateAgent({
        topic: resolvedTopic || "Custom Interview",
        role,
        years_exp: yearsExp,
        difficulty,
        target_turns: numQuestions,
        jd_text: isJdBased ? jdText : undefined,
      });
      localStorage.setItem(
        "jp_interview_session",
        JSON.stringify({
          session_id: res.session_id,
          thread_id: res.thread_id,
          current_question: res.first_question,
          question_number: 1,
          followup_depth: 0,
          target_turns: res.target_turns,
          topic_clusters: res.topic_clusters,
          agent_mode: true,
        }),
      );
    } else {
      const res = await mutateAsync({
        topic: resolvedTopic || "Custom Interview",
        role,
        years_exp: yearsExp,
        num_questions: useCustomQ ? parsedCustomQ.length : numQuestions,
        difficulty,
        jd_text: !useCustomQ && isJdBased ? jdText : undefined,
        custom_questions: useCustomQ ? parsedCustomQ : undefined,
      });
      localStorage.setItem(
        "jp_interview_session",
        JSON.stringify({
          session_id: res.session_id,
          questions: res.questions,
          total_questions: res.total_questions,
        }),
      );
    }
    router.push("/interview/session");
  }

  return (
    <div>
      {/* ── Step 1: Topic ── */}
      <SectionHeading
        step="1"
        title="What are you practicing?"
        subtitle="Pick an interview style or a technology you want to be tested on"
      />

      {/* Interview type cards */}
      <div className="grid grid-cols-3 gap-2.5 mb-5">
        {INTERVIEW_TYPES.map(({ label, icon: Icon, desc }) => {
          const active = selectedType === label && !customTopic.trim();
          return (
            <button
              key={label}
              onClick={() => pickType(label)}
              className={`group text-left px-4 py-3 rounded-xl border-2 transition-all duration-150 ${
                active
                  ? "border-indigo-500 bg-indigo-500/6"
                  : "border-[var(--color-border)] hover:border-indigo-300 hover:bg-[var(--color-surface)]"
              }`}
            >
              <div className="flex items-center gap-2.5 mb-1.5">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                    active
                      ? "bg-indigo-500 text-white"
                      : "bg-[var(--color-border)] text-[var(--color-text-3)] group-hover:bg-indigo-500/10 group-hover:text-indigo-500"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <p className={`font-semibold text-sm ${active ? "text-indigo-500" : ""}`}>{label}</p>
              </div>
              <p className="text-xs text-[var(--color-text-3)] leading-snug pl-[38px]">{desc}</p>
            </button>
          );
        })}
      </div>

      {/* JD textarea */}
      {isJdBased && (
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={5}
          placeholder="Paste the job description here — questions will be tailored directly to its requirements."
          className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm resize-none placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-5"
        />
      )}

      {/* Tech chips */}
      <p className="text-xs text-[var(--color-text-3)] mb-2.5 font-medium">or pick a technology</p>
      <div className="flex flex-wrap gap-2 mb-4">
        {TECH_CHIPS.map((chip) => {
          const active = selectedTech === chip && !customTopic.trim();
          return (
            <button
              key={chip}
              onClick={() => pickTech(chip)}
              className={`px-3.5 py-1.5 rounded-xl border text-sm font-medium transition-all ${
                active
                  ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                  : "border-[var(--color-border)] text-[var(--color-text-2)] hover:border-indigo-300"
              }`}
            >
              {chip}
            </button>
          );
        })}
      </div>

      {/* Custom input */}
      <input
        type="text"
        placeholder="Or type anything — Spring Security, LangChain RAG, Kafka…"
        value={customTopic}
        onChange={(e) => onCustomChange(e.target.value)}
        className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />

      {resolvedTopic && (
        <p className="text-xs text-indigo-500 font-semibold mt-2 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          {resolvedTopic}
        </p>
      )}

      <Divider />

      {/* ── Adaptive AI Mode Toggle ── */}
      <div className={`flex items-center justify-between mb-4 p-3.5 rounded-xl border transition-all ${
        agentMode ? "border-violet-500 bg-violet-500/6" : "border-[var(--color-border)]"
      }`}>
        <div>
          <p className="text-sm font-semibold text-[var(--color-text)] flex items-center gap-2">
            <span>Adaptive AI Mode</span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-violet-500/15 text-violet-500">BETA</span>
          </p>
          <p className="text-xs text-[var(--color-text-3)] mt-0.5">
            LangGraph agent — dynamic follow-ups, real-time difficulty adaptation
          </p>
        </div>
        <button
          onClick={() => { setAgentMode((v) => !v); setUseCustomQ(false); }}
          className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors ${
            agentMode ? "bg-violet-600" : "bg-[var(--color-border)]"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              agentMode ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>

      {/* ── Custom Questions Toggle ── */}
      {!agentMode && (
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text)]">Use my own questions</p>
          <p className="text-xs text-[var(--color-text-3)] mt-0.5">Skip AI generation — paste your question list</p>
        </div>
        <button
          onClick={() => setUseCustomQ((v) => !v)}
          className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors ${
            useCustomQ ? "bg-indigo-600" : "bg-[var(--color-border)]"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              useCustomQ ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>
      )}

      {useCustomQ && (
        <>
          <textarea
            value={customQText}
            onChange={(e) => setCustomQText(e.target.value)}
            rows={6}
            placeholder={`One question per line:\nWhat is a closure in JavaScript?\nExplain REST vs GraphQL trade-offs\nHow would you design a rate limiter?`}
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm resize-none placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {parsedCustomQ.length > 0 && (
            <p className="text-xs text-indigo-500 font-medium mt-1.5">
              {parsedCustomQ.length} question{parsedCustomQ.length !== 1 ? "s" : ""} ready
            </p>
          )}
        </>
      )}

      {!useCustomQ && (
        <>
          <Divider />

          {/* ── Step 2: Difficulty ── */}
          <SectionHeading step="2" title="Difficulty level" />

          <div className="grid grid-cols-3 gap-2.5">
            {DIFFICULTIES.map((d) => {
              const active = difficulty === d.key;
              return (
                <button
                  key={d.key}
                  onClick={() => setDifficulty(d.key)}
                  className={`relative overflow-hidden text-left px-4 py-3 rounded-xl border-2 transition-all duration-150 ${
                    active
                      ? `${d.activeBorder} ${d.activeBg}`
                      : "border-[var(--color-border)] hover:border-[var(--color-text-3)]"
                  }`}
                >
                  {active && <div className={`absolute inset-x-0 top-0 h-0.5 ${d.activeBar}`} />}
                  <div className="flex items-center gap-2">
                    <span className="text-base">{d.emoji}</span>
                    <p className={`font-bold text-sm ${active ? d.activeText : ""}`}>{d.label}</p>
                  </div>
                  <p className="text-xs text-[var(--color-text-3)] mt-1 leading-snug">{d.desc}</p>
                </button>
              );
            })}
          </div>

          <Divider />

          {/* ── Step 3: Questions ── */}
          <SectionHeading step="3" title="How many questions?" />
          <DotPicker value={numQuestions} onChange={setNumQuestions} />
        </>
      )}

      <Divider />

      {/* ── Step 4: Role + Exp ── */}
      <SectionHeading step="4" title="Your background" />

      <div className="grid grid-cols-[1fr_auto] gap-5 items-start">
        <div>
          <p className="text-xs font-medium text-[var(--color-text-3)] mb-2">Role</p>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {ROLES.map((r) => <option key={r}>{r}</option>)}
          </select>
        </div>

        <div>
          <p className="text-xs font-medium text-[var(--color-text-3)] mb-2">Experience (yrs)</p>
          <div className="flex gap-1.5">
            {EXP_OPTIONS.map((e) => (
              <button
                key={e}
                onClick={() => setYearsExp(e)}
                className={`px-3 py-2.5 rounded-xl border text-sm font-medium transition-all whitespace-nowrap ${
                  yearsExp === e
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                    : "border-[var(--color-border)] text-[var(--color-text-2)] hover:border-indigo-300"
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>
      </div>

      {(error || agentError) && (
        <div className="mt-5 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl">
          {((error || agentError) as Error).message}
        </div>
      )}

      {/* ── CTA ── */}
      <div className="mt-8">
        <button
          onClick={handleStart}
          disabled={!canStart}
          className={`w-full py-4 rounded-2xl font-bold text-[15px] transition-all flex items-center justify-center gap-3 ${
            canStart
              ? agentMode
                ? "bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow-xl shadow-violet-500/25"
                : "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-xl shadow-indigo-500/25"
              : "bg-[var(--color-border)] text-[var(--color-text-3)] cursor-not-allowed"
          }`}
        >
          {anyPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {agentMode ? "Initialising agent…" : "Generating questions…"}
            </>
          ) : (
            <>
              <Mic className="w-4 h-4" />
              {agentMode ? "Start Adaptive Interview" : "Start Interview"}
              {agentMode ? (
                <span className="text-xs font-normal opacity-70">
                  {resolvedTopic} · {difficulty} · up to {numQuestions}q
                </span>
              ) : useCustomQ ? (
                <span className="text-xs font-normal opacity-70">
                  {parsedCustomQ.length} custom question{parsedCustomQ.length !== 1 ? "s" : ""}
                </span>
              ) : resolvedTopic ? (
                <span className="text-xs font-normal opacity-70">
                  {resolvedTopic} · {difficulty} · {numQuestions}q
                </span>
              ) : null}
            </>
          )}
        </button>
      </div>
    </div>
  );
}

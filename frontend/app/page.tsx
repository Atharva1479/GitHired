import type { ReactNode } from "react";

import {
  ArrowRight,
  AudioLines,
  BarChart2,
  Bell,
  BookOpen,
  Briefcase,
  Check,
  CheckCircle2,
  ChevronRight,
  Code2,
  Flame,
  Medal,
  Mic,
  ScanText,
  Sparkles,
  Target,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";

import { HeroVoicePearl } from "@/components/pilot/HeroVoicePearl";

export default function LandingPage() {
  return (
    <div className="flex-1 flex flex-col bg-white">
      <LandingNav />
      <Hero />
      <PillarTrack />
      <PillarLearn />
      <PillarPractice />
      <PillarMotivate />
      <PillarATS />
      <PillarInterview />
      <HowItWorks />
      <Comparison />
      <FinalCTA />
      <Footer />
    </div>
  );
}

/* ── NAV ─────────────────────────────────────────────────────────────── */

function LandingNav() {
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-gray-100">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white grid place-items-center shadow-sm">
            <Briefcase className="w-4 h-4" />
          </span>
          <span className="text-[16px] font-semibold tracking-tight text-gray-900 group-hover:text-indigo-700 transition-colors">
            GitHired
          </span>
        </Link>
        <nav className="hidden md:flex items-center gap-8 text-[14px] text-gray-600">
          <a href="#track" className="hover:text-gray-900 transition-colors">Track</a>
          <a href="#learn" className="hover:text-gray-900 transition-colors">Learn</a>
          <a href="#practice" className="hover:text-gray-900 transition-colors">Practice</a>
          <a href="#motivate" className="hover:text-gray-900 transition-colors">Motivate</a>
          <a href="#ats" className="hover:text-gray-900 transition-colors">ATS</a>
          <a href="#interview" className="hover:text-gray-900 transition-colors">Interview</a>
          <a href="#why" className="hover:text-gray-900 transition-colors">Why</a>
        </nav>
        <div className="flex items-center gap-1.5">
          <Link
            href="/login"
            className="hidden sm:inline-flex items-center rounded-lg px-3 h-9 text-[13.5px] font-medium text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 hover:bg-black text-white px-3.5 h-9 text-[13.5px] font-medium shadow-sm transition-colors"
          >
            Get started
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}

/* ── HERO ─────────────────────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(99,102,241,0.10) 0%, rgba(255,255,255,0) 60%), radial-gradient(50% 40% at 90% 10%, rgba(236,72,153,0.06) 0%, rgba(255,255,255,0) 60%)",
        }}
      />
      <div className="max-w-6xl mx-auto px-6 pt-20 pb-24 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 ring-1 ring-indigo-200 px-3 py-1 text-[12px] font-medium text-indigo-700 mb-6">
            <Sparkles className="w-3 h-3" />
            AI voice agent · ATS Scanner · DSA Practice · AI Mock Interview · Gamification
          </span>
          <h1 className="text-[44px] sm:text-[56px] lg:text-[64px] font-bold tracking-tight text-gray-900 leading-[1.02]">
            Track. Study.{" "}
            <span className="text-indigo-600">Land the job.</span>
          </h1>
          <p className="mt-6 text-[17px] text-gray-600 max-w-xl leading-relaxed">
            GitHired is your complete job-hunt platform — kanban pipeline,
            referral tracking, ATS resume scoring, AI study plans, a voice agent
            that acts for you, and daily XP to keep you consistent when motivation dips.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-5 h-12 font-medium text-[15px] shadow-sm transition-colors"
            >
              Sign in with Google
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#track"
              className="inline-flex items-center gap-2 rounded-lg bg-white ring-1 ring-gray-300 hover:bg-gray-50 text-gray-900 px-5 h-12 font-medium text-[15px] shadow-sm transition-colors"
            >
              See the features
            </a>
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-4 text-[13px] text-gray-500">
            <span className="inline-flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              Free to use
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              Sign in with Google
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              Built for junior devs
            </span>
          </div>
        </div>
        <PilotChatMock />
      </div>
    </section>
  );
}

function PilotChatMock() {
  return (
    <div className="relative pb-8 pr-8">
      <div
        aria-hidden
        className="absolute -inset-6 rounded-3xl"
        style={{
          background:
            "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(236,72,153,0.08))",
          filter: "blur(40px)",
        }}
      />
      {/* Light-mode chat panel */}
      <div className="relative rounded-2xl bg-white ring-1 ring-gray-200 shadow-xl overflow-hidden">
        {/* window chrome */}
        <div className="flex items-center gap-1.5 px-4 pt-3 pb-2.5 border-b border-gray-100 bg-gray-50/80">
          <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
          <span className="ml-3 text-[11px] font-mono text-gray-400">Jarvis — AI job-hunt assistant</span>
        </div>
        {/* chat messages */}
        <div className="px-4 py-4 space-y-3">
          <div className="flex justify-end">
            <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-indigo-600 text-white px-3 py-2 text-[13px]">
              What should I focus on today?
            </div>
          </div>
          <div className="flex gap-2.5 items-start">
            <span className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 grid place-items-center shrink-0 mt-0.5 shadow-sm">
              <Sparkles className="w-3 h-3 text-white" />
            </span>
            <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-gray-100 text-gray-800 px-3 py-2.5 text-[13px] leading-relaxed space-y-1.5">
              <p className="font-medium text-gray-900">Here&apos;s your priority list:</p>
              <p className="text-gray-600">1. <span className="text-amber-600 font-medium">Follow up with Stripe</span> — 9 days, no reply.</p>
              <p className="text-gray-600">2. <span className="text-emerald-600 font-medium">Referral ask to Rohan</span> — accepted your invite.</p>
              <p className="text-gray-600">3. <span className="text-violet-600 font-medium">3 DSA topics due</span> today.</p>
            </div>
          </div>
          <div className="flex justify-end">
            <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-indigo-600 text-white px-3 py-2 text-[13px]">
              Draft the Stripe follow-up.
            </div>
          </div>
          <div className="flex gap-2.5 items-start">
            <span className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 grid place-items-center shrink-0 mt-0.5 shadow-sm">
              <Sparkles className="w-3 h-3 text-white" />
            </span>
            <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-gray-100 text-gray-800 px-3 py-2.5 text-[13px] leading-relaxed">
              <p className="text-[11px] font-semibold text-emerald-600 mb-1">Draft ready</p>
              <p className="text-gray-600 text-[12px]">Hi [Recruiter], I wanted to follow up on my Frontend Engineer application…</p>
            </div>
          </div>
        </div>
        {/* input bar */}
        <div className="flex items-center gap-2 px-4 pb-4">
          <div className="flex-1 rounded-xl bg-gray-50 text-gray-400 text-[12.5px] px-3 py-2 ring-1 ring-gray-200">
            Ask Jarvis anything…
          </div>
        </div>
      </div>

      {/* Voice mode — what opens when you click the pearl */}
      <div className="absolute bottom-0 right-0 flex flex-col items-center gap-1">
        <div className="rounded-full bg-gray-900/90 text-white text-[11px] px-3 py-1.5 shadow-lg font-medium backdrop-blur-sm">
          Click to speak…
        </div>
        <HeroVoicePearl />
        <span className="text-[10.5px] text-gray-400 font-medium tracking-wide uppercase">
          Voice mode
        </span>
      </div>
    </div>
  );
}

/* ── PILLAR 1: TRACK ─────────────────────────────────────────────────── */

function PillarTrack() {
  return (
    <section id="track" className="py-24 border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-orange-600" n="01" label="Track" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              Every application and referral,{" "}
              <span className="text-orange-500">organized.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Stop losing track of where things stand. GitHired gives you a
              visual pipeline for every role and a stage-by-stage referral
              tracker — plus time-aware nudges so nothing falls through the
              cracks.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<Target className="w-5 h-5" />}
                tone="orange"
                title="Kanban Pipeline"
                body="Applied → Screening → Interview → Offer. Drag to update, attach resumes and JDs."
              />
              <FeatureCard
                icon={<Users className="w-5 h-5" />}
                tone="orange"
                title="Referral Tracker"
                body="Invite → Accepted → Message Sent → Referred. Never lose a warm intro."
              />
              <FeatureCard
                icon={<Bell className="w-5 h-5" />}
                tone="orange"
                title="Smart Nudges"
                body="Eight rules watch your data and surface 3–5 actions worth doing today."
              />
              <FeatureCard
                icon={<Sparkles className="w-5 h-5" />}
                tone="orange"
                title="AI Follow-ups"
                body="One click drafts a personalized follow-up email or referral ask. Copy and send."
              />
            </div>
          </div>
          <KanbanMock />
        </div>
      </div>
    </section>
  );
}

function KanbanMock() {
  return (
    <div className="rounded-2xl bg-gray-50 ring-1 ring-gray-200 p-4 shadow-sm">
      <div className="rounded-xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          <span className="w-2 h-2 rounded-full bg-amber-400" />
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="ml-2 text-[11px] font-mono text-gray-400">githired.app/applications</span>
        </div>
        <div className="p-3 grid grid-cols-2 md:grid-cols-4 gap-2">
          <MockColumn status="Applied" color="bg-blue-500" cards={[
            { co: "Stripe", role: "Frontend Eng", days: 9 },
            { co: "Linear", role: "Software Eng", days: 4 },
          ]} />
          <MockColumn status="Screening" color="bg-violet-500" cards={[
            { co: "Datadog", role: "Backend Eng", days: 11 },
          ]} />
          <MockColumn status="Interview" color="bg-amber-500" cards={[
            { co: "Anthropic", role: "Eval Eng", days: 14 },
          ]} />
          <MockColumn status="Offer" color="bg-emerald-500" cards={[
            { co: "Plaid", role: "FE Engineer", days: 21 },
          ]} />
        </div>
      </div>
    </div>
  );
}

/* ── PILLAR 2: LEARN ─────────────────────────────────────────────────── */

function PillarLearn() {
  return (
    <section id="learn" className="py-24 bg-gray-50 border-y border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-emerald-600" n="02" label="Learn" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <StudyMock />
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              AI builds your study plan.{" "}
              <span className="text-emerald-600">You execute it.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Tell Jarvis your target role and companies — it generates a
              structured revision tree of sections, subsections, and topics.
              Track each topic by status and let the AI fill gaps as you go.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<BookOpen className="w-5 h-5" />}
                tone="emerald"
                title="Study Mode"
                body="AI-generated revision trees for any role. Mark topics done, in progress, or mastered."
              />
              <FeatureCard
                icon={<Sparkles className="w-5 h-5" />}
                tone="emerald"
                title="AI Jarvis Chat"
                body="Ask about your prep, generate topics, or get a daily priority list — by text or voice."
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function StudyMock() {
  const topics = [
    { name: "Spring Boot & Auto-configuration", done: true },
    { name: "REST API design with Spring MVC", done: true },
    { name: "JPA / Hibernate & lazy loading", done: true },
    { name: "Microservices with Spring Cloud", done: false },
    { name: "Docker & container basics", done: false },
  ];
  return (
    <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-emerald-600" />
        <span className="text-[13px] font-semibold text-gray-900">Study — Full Stack Java Developer</span>
      </div>
      {/* progress */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[12px] text-gray-500">Spring & Backend</span>
          <span className="text-[11px] text-gray-400">3/5 done</span>
        </div>
        <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400" style={{ width: "60%" }} />
        </div>
      </div>
      {/* topic list */}
      <ul className="divide-y divide-gray-50">
        {topics.map((t) => (
          <li key={t.name} className="flex items-center gap-3 px-4 py-2.5">
            <span className={`w-4 h-4 rounded grid place-items-center shrink-0 ${t.done ? "bg-emerald-500" : "bg-gray-100 ring-1 ring-gray-200"}`}>
              {t.done ? <Check className="w-2.5 h-2.5 text-white" /> : null}
            </span>
            <span className={`text-[13px] ${t.done ? "text-gray-400 line-through" : "text-gray-800"}`}>
              {t.name}
            </span>
            {!t.done ? (
              <span className="ml-auto text-[10px] text-violet-600 bg-violet-50 ring-1 ring-violet-200 rounded-full px-2 py-0.5">due</span>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/60 flex items-center gap-2">
        <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
        <span className="text-[12px] text-gray-500">Ask Jarvis to generate more topics…</span>
      </div>
    </div>
  );
}

/* ── PILLAR 3: PRACTICE ──────────────────────────────────────────────── */

function PillarPractice() {
  return (
    <section id="practice" className="py-24 border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-blue-600" n="03" label="Practice" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              Log every DSA problem.{" "}
              <span className="text-blue-600">Let AI coach you through it.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Track every problem you solve, paste your solution, and get instant
              AI feedback — time and space complexity, approach analysis, an
              optimized alternative, and a step-by-step dry run. Know exactly
              where your gaps are before the interview.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<Code2 className="w-5 h-5" />}
                tone="blue"
                title="Problem Log"
                body="Easy · Medium · Hard. Organized by topic. Add your solution in the editor and save in one click."
              />
              <FeatureCard
                icon={<Sparkles className="w-5 h-5" />}
                tone="blue"
                title="AI Code Review"
                body="Paste your solution → AI returns complexity, approach critique, and a cleaned-up optimal version."
              />
              <FeatureCard
                icon={<BarChart2 className="w-5 h-5" />}
                tone="blue"
                title="Topic Stats"
                body="See which topics you've covered, how many are AI-reviewed, and where you're weakest."
              />
              <FeatureCard
                icon={<Flame className="w-5 h-5" />}
                tone="blue"
                title="Daily Streak"
                body="Solve at least one problem per day to build your DSA streak. Earn XP for every problem logged and analyzed."
              />
            </div>
          </div>
          <DsaMock />
        </div>
      </div>
    </section>
  );
}

function DsaMock() {
  const problems = [
    { title: "Two Sum", difficulty: "easy", topic: "Arrays", analyzed: true },
    { title: "LRU Cache", difficulty: "medium", topic: "Design", analyzed: true },
    { title: "Trapping Rain Water", difficulty: "hard", topic: "Arrays", analyzed: false },
  ];
  const diffStyle: Record<string, string> = {
    easy: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
    medium: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
    hard: "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
  };
  return (
    <div className="space-y-3">
      {/* Stats strip */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[13px] font-semibold text-gray-900">DSA Practice</span>
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-orange-600 bg-orange-50 ring-1 ring-orange-200 rounded-full px-2.5 py-0.5">
            <Flame className="w-3 h-3" /> 14d streak
          </span>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-[22px] font-bold text-gray-900">45</div>
            <div className="text-[11px] text-gray-500">solved</div>
          </div>
          <div className="flex-1 grid grid-cols-3 gap-2">
            {[
              { label: "Easy", count: 20, cls: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
              { label: "Medium", count: 18, cls: "bg-amber-50 text-amber-700 ring-amber-200" },
              { label: "Hard", count: 7, cls: "bg-rose-50 text-rose-700 ring-rose-200" },
            ].map((d) => (
              <div key={d.label} className={`rounded-lg ring-1 px-2 py-1.5 text-center ${d.cls}`}>
                <div className="text-[15px] font-bold">{d.count}</div>
                <div className="text-[10px]">{d.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Problem list */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-blue-600" />
          <span className="text-[12px] font-semibold text-gray-900">Recent problems</span>
        </div>
        <ul className="divide-y divide-gray-50">
          {problems.map((p) => (
            <li key={p.title} className="flex items-center gap-3 px-4 py-2.5">
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${diffStyle[p.difficulty]}`}>
                {p.difficulty}
              </span>
              <span className="flex-1 text-[13px] text-gray-800 truncate">{p.title}</span>
              <span className="text-[10.5px] text-gray-400">{p.topic}</span>
              {p.analyzed ? (
                <span className="inline-flex items-center gap-0.5 text-[10px] text-indigo-600 bg-indigo-50 ring-1 ring-indigo-200 rounded-full px-1.5 py-0.5">
                  <Sparkles className="w-2.5 h-2.5" /> AI
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>

      {/* AI analysis preview */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
          <span className="text-[12px] font-semibold text-gray-900">AI Analysis — Two Sum</span>
          <span className="ml-auto text-[10px] text-violet-600 bg-violet-50 ring-1 ring-violet-200 rounded-full px-1.5 py-0.5">Gemini</span>
        </div>
        <div className="px-4 py-3 space-y-3">
          {/* Complexity row */}
          <div className="flex gap-3">
            <div className="flex-1 rounded-lg bg-gray-50 ring-1 ring-gray-200 p-2.5 text-center">
              <div className="text-[10.5px] text-gray-400 uppercase tracking-wider mb-0.5">Time</div>
              <code className="text-[16px] font-bold text-violet-600">O(n)</code>
            </div>
            <div className="flex-1 rounded-lg bg-gray-50 ring-1 ring-gray-200 p-2.5 text-center">
              <div className="text-[10.5px] text-gray-400 uppercase tracking-wider mb-0.5">Space</div>
              <code className="text-[16px] font-bold text-violet-600">O(n)</code>
            </div>
            <div className="flex-1 rounded-lg bg-emerald-50 ring-1 ring-emerald-200 p-2.5 text-center">
              <div className="text-[10.5px] text-emerald-600 uppercase tracking-wider mb-0.5">Score</div>
              <span className="text-[16px] font-bold text-emerald-600">9/10</span>
            </div>
          </div>
          {/* Critique */}
          <p className="text-[12px] text-gray-600 leading-relaxed">
            <span className="font-medium text-gray-800">Approach:</span> Hash map complement lookup. One pass — optimal. Minor: variable names could be clearer.
          </p>
          {/* Optimal solution */}
          <div className="rounded-lg bg-gray-50 ring-1 ring-gray-200 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-200">
              <span className="text-[10px] text-gray-400 font-mono">optimal solution</span>
              <span className="text-[10px] text-emerald-600 font-semibold">AI suggested</span>
            </div>
            <pre className="px-3 py-2.5 text-[11px] leading-relaxed overflow-x-auto"><code className="text-gray-700">{`def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target-num], i]
        seen[num] = i`}</code></pre>
          </div>
          {/* Explanation */}
          <div className="rounded-lg bg-blue-50 ring-1 ring-blue-100 px-3 py-2 text-[11.5px] text-blue-800 leading-snug">
            <span className="font-semibold">Explanation:</span> Store each number&apos;s index as you iterate. For every element, check if its complement already exists in the map — if yes, you have your answer in a single O(n) pass with O(n) space.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── PILLAR 4: MOTIVATE ──────────────────────────────────────────────── */

function PillarMotivate() {
  return (
    <section id="motivate" className="py-24 border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-violet-600" n="04" label="Stay Motivated" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              Turn consistency into a game{" "}
              <span className="text-violet-600">you want to win.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Job hunts drag on for weeks. GitHired keeps you showing up every
              day with XP, streaks, achievements, daily quests, and a voice agent
              you can talk to hands-free while commuting.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<Zap className="w-5 h-5" />}
                tone="violet"
                title="XP & Levels"
                body="Earn XP for applications, study sessions, follow-ups. Level up as you grind."
              />
              <FeatureCard
                icon={<Flame className="w-5 h-5" />}
                tone="violet"
                title="Daily Streaks"
                body="Build a streak by completing daily quests. Freeze tokens protect your streak on off days."
              />
              <FeatureCard
                icon={<Trophy className="w-5 h-5" />}
                tone="violet"
                title="Achievements"
                body="Bronze to platinum badges for milestones — First Apply, Referral Machine, 7-day streak, and more."
              />
              <FeatureCard
                icon={<AudioLines className="w-5 h-5" />}
                tone="violet"
                title="Voice Agent"
                body="Talk to Jarvis hands-free. Log applications, get priorities, send follow-ups — by voice."
              />
            </div>
          </div>
          <GamifyMock />
        </div>
      </div>
    </section>
  );
}

function GamifyMock() {
  return (
    <div className="space-y-3">
      {/* XP bar card */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 grid place-items-center text-white text-[11px] font-bold">
              12
            </span>
            <div>
              <div className="text-[13px] font-semibold text-gray-900">Level 12</div>
              <div className="text-[11px] text-gray-400">Senior Applicant</div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-orange-50 ring-1 ring-orange-200">
            <Flame className="w-3.5 h-3.5 text-orange-500" />
            <span className="text-[12px] font-bold text-gray-900">14</span>
            <span className="text-[11px] text-gray-500">day streak</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" style={{ width: "68%" }} />
          </div>
          <span className="text-[11px] text-gray-400 tabular-nums shrink-0">1 360 / 2 000 XP</span>
        </div>
      </div>

      {/* Daily quests */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Medal className="w-4 h-4 text-amber-500" />
          <span className="text-[13px] font-semibold text-gray-900">Daily quests</span>
          <span className="ml-auto text-[11px] text-emerald-600 bg-emerald-50 ring-1 ring-emerald-200 rounded-full px-2 py-0.5">2 / 3 done</span>
        </div>
        <div className="space-y-2">
          {[
            { label: "Apply to 1 role", xp: 50, done: true },
            { label: "Log a study session", xp: 30, done: true },
            { label: "Send a follow-up", xp: 40, done: false },
          ].map((q) => (
            <div key={q.label} className="flex items-center gap-2.5">
              <span className={`w-4 h-4 rounded-full grid place-items-center shrink-0 ${q.done ? "bg-emerald-500" : "bg-gray-100 ring-1 ring-gray-200"}`}>
                {q.done ? <Check className="w-2.5 h-2.5 text-white" /> : null}
              </span>
              <span className={`flex-1 text-[12.5px] ${q.done ? "line-through text-gray-400" : "text-gray-700"}`}>{q.label}</span>
              <span className="text-[11px] font-medium text-indigo-600">+{q.xp} XP</span>
            </div>
          ))}
        </div>
      </div>

      {/* Achievements */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="text-[13px] font-semibold text-gray-900 mb-3">Recent achievements</div>
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { label: "First Apply", color: "bg-amber-50 text-amber-700 ring-amber-200" },
            { label: "7-Day Streak", color: "bg-orange-50 text-orange-700 ring-orange-200" },
            { label: "Referral Machine", color: "bg-violet-50 text-violet-700 ring-violet-200" },
            { label: "Study Starter", color: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
          ].map((a) => (
            <span key={a.label} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ${a.color}`}>
              <Trophy className="w-2.5 h-2.5" />
              {a.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── PILLAR 5: ATS SCORE ─────────────────────────────────────────────── */

function PillarATS() {
  return (
    <section id="ats" className="py-24 bg-gray-50 border-y border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-rose-600" n="05" label="Score" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <AtsMock />
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              Know your ATS score{" "}
              <span className="text-rose-600">before you apply.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Upload your resume and paste the job description — GitHired&apos;s
              ML-powered ATS engine scores you across 8 dimensions in seconds.
              See exactly which keywords are missing and fix them before a
              recruiter even sees your name.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<ScanText className="w-5 h-5" />}
                tone="rose"
                title="8-Dimension Score"
                body="Keyword placement, semantic match, ontology coverage, experience, education, and more — one composite score."
              />
              <FeatureCard
                icon={<Sparkles className="w-5 h-5" />}
                tone="rose"
                title="ML Semantic Match"
                body="Word2Vec + MiniLM sentence embeddings catch synonyms and paraphrases that exact-match scanners miss."
              />
              <FeatureCard
                icon={<BarChart2 className="w-5 h-5" />}
                tone="rose"
                title="Keyword Gap Report"
                body="Colour-coded list of matched, missing, and semantically-similar keywords with placement suggestions."
              />
              <FeatureCard
                icon={<CheckCircle2 className="w-5 h-5" />}
                tone="rose"
                title="Section Checklist"
                body="Instant check on whether your resume has Experience, Skills, Education, and Projects sections ATS scanners expect."
              />
            </div>
            <div className="mt-6">
              <Link
                href="/ats"
                className="inline-flex items-center gap-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white px-5 h-10 font-medium text-[14px] shadow-sm transition-colors"
              >
                <ScanText className="w-4 h-4" />
                Score my resume free
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function AtsMock() {
  const categories = [
    { label: "Keyword Placement", score: 91, color: "bg-emerald-500" },
    { label: "Semantic Match",    score: 84, color: "bg-violet-500" },
    { label: "Required Coverage", score: 80, color: "bg-blue-500" },
    { label: "Experience Fit",    score: 75, color: "bg-amber-500" },
  ];

  const matched = ["React", "TypeScript", "Node.js", "REST API", "Git"];
  const missing = ["GraphQL", "AWS", "Docker"];

  return (
    <div className="space-y-3">
      {/* Score gauge card */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-5 shadow-sm flex items-center gap-6">
        {/* SVG circular gauge */}
        <div className="relative shrink-0">
          <svg width="88" height="88" viewBox="0 0 88 88">
            <circle cx="44" cy="44" r="36" fill="none" stroke="#f3f4f6" strokeWidth="8" />
            <circle
              cx="44" cy="44" r="36"
              fill="none"
              stroke="#e11d48"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 36}`}
              strokeDashoffset={`${2 * Math.PI * 36 * (1 - 0.87)}`}
              transform="rotate(-90 44 44)"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[22px] font-bold text-gray-900 leading-none">87</span>
            <span className="text-[10px] text-gray-400 mt-0.5">/ 100</span>
          </div>
        </div>
        <div>
          <div className="text-[13px] font-semibold text-gray-900">ATS Score</div>
          <div className="mt-1 inline-flex items-center gap-1 rounded-full bg-emerald-50 ring-1 ring-emerald-200 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
            <CheckCircle2 className="w-3 h-3" /> Strong match
          </div>
          <div className="mt-2 text-[11.5px] text-gray-500">
            Resume: <span className="text-gray-700 font-medium">Atharva_Resume.pdf</span>
          </div>
          <div className="text-[11.5px] text-gray-500">
            Role: <span className="text-gray-700 font-medium">Frontend Engineer · Stripe</span>
          </div>
        </div>
      </div>

      {/* Category breakdown */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <BarChart2 className="w-3.5 h-3.5 text-rose-600" />
          <span className="text-[12px] font-semibold text-gray-900">Score breakdown</span>
          <span className="ml-auto text-[10px] text-violet-600 bg-violet-50 ring-1 ring-violet-200 rounded-full px-1.5 py-0.5">ML</span>
        </div>
        <div className="space-y-2.5">
          {categories.map((c) => (
            <div key={c.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11.5px] text-gray-700">{c.label}</span>
                <span className="text-[11px] font-semibold text-gray-900">{c.score}</span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${c.color}`}
                  style={{ width: `${c.score}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Keyword analysis */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <ScanText className="w-3.5 h-3.5 text-rose-600" />
          <span className="text-[12px] font-semibold text-gray-900">Keyword analysis</span>
        </div>
        <div className="space-y-2">
          <div>
            <div className="text-[10.5px] text-gray-400 uppercase tracking-wider mb-1.5">Matched ({matched.length})</div>
            <div className="flex flex-wrap gap-1.5">
              {matched.map((kw) => (
                <span key={kw} className="inline-flex items-center gap-1 rounded-full bg-emerald-50 ring-1 ring-emerald-200 px-2 py-0.5 text-[10.5px] font-medium text-emerald-700">
                  <Check className="w-2.5 h-2.5" />{kw}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div className="text-[10.5px] text-gray-400 uppercase tracking-wider mb-1.5">Missing ({missing.length})</div>
            <div className="flex flex-wrap gap-1.5">
              {missing.map((kw) => (
                <span key={kw} className="inline-flex items-center rounded-full bg-rose-50 ring-1 ring-rose-200 px-2 py-0.5 text-[10.5px] font-medium text-rose-700">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* AI suggestions */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-violet-500" />
          <span className="text-[12px] font-semibold text-gray-900">AI suggestions</span>
          <span className="ml-auto text-[10px] text-violet-600 bg-violet-50 ring-1 ring-violet-200 rounded-full px-1.5 py-0.5">+8 pts potential</span>
        </div>
        <div className="px-4 py-3 space-y-2.5">
          {[
            {
              tag: "Skills section",
              color: "text-amber-700 bg-amber-50 ring-amber-200",
              tip: 'Add "GraphQL" and "AWS Lambda" — both appear 4× in this JD.',
            },
            {
              tag: "Experience bullet",
              color: "text-blue-700 bg-blue-50 ring-blue-200",
              tip: 'Rephrase "built APIs" → "designed and deployed REST & GraphQL APIs on AWS" to match JD phrasing.',
            },
            {
              tag: "Summary line",
              color: "text-rose-700 bg-rose-50 ring-rose-200",
              tip: 'Mention "Docker" and "containerization" — required skills missing from your summary.',
            },
          ].map((s) => (
            <div key={s.tag} className="flex items-start gap-2.5">
              <span className={`shrink-0 mt-0.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ${s.color}`}>
                {s.tag}
              </span>
              <p className="text-[11.5px] text-gray-600 leading-snug">{s.tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── PILLAR 6: AI MOCK INTERVIEW ─────────────────────────────────────── */

function PillarInterview() {
  return (
    <section id="interview" className="py-24 border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <PillarLabel color="text-indigo-600" n="06" label="Interview" />
        <div className="mt-4 grid lg:grid-cols-2 gap-12 items-start">
          <div>
            <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
              Practice interviews that{" "}
              <span className="text-indigo-600">actually score you.</span>
            </h2>
            <p className="mt-4 text-[16px] text-gray-600 leading-relaxed">
              Pick a topic, difficulty, and number of questions — the AI asks by
              voice, you answer out loud, and Groq Whisper transcribes everything.
              After the session you get a full scored report with ideal answers
              and skill-level breakdown so you know exactly what to fix.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-3">
              <FeatureCard
                icon={<Mic className="w-5 h-5" />}
                tone="indigo"
                title="Voice Q&A"
                body="AI asks questions via TTS. Record your answer by mic — just like a real phone screen or HackerEarth Helix round."
              />
              <FeatureCard
                icon={<Sparkles className="w-5 h-5" />}
                tone="indigo"
                title="AI Evaluation"
                body="Every answer scored 0–10 with ideal answer examples and specific, constructive feedback from Gemini."
              />
              <FeatureCard
                icon={<BarChart2 className="w-5 h-5" />}
                tone="indigo"
                title="Skill Breakdown"
                body="Post-interview report calibrated to interview type: Communication, Technical Depth, Problem Solving, Clarity."
              />
              <FeatureCard
                icon={<Target className="w-5 h-5" />}
                tone="indigo"
                title="Any Topic or Difficulty"
                body="HR Behavioral, System Design, JD-based, or any tech stack (Java, Spring Boot, React…). Easy, Medium, or Hard."
              />
            </div>
            <div className="mt-6">
              <a
                href="/interview"
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-5 h-10 font-medium text-[14px] shadow-sm transition-colors"
              >
                <Mic className="w-4 h-4" />
                Try a mock interview
                <ArrowRight className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
          <InterviewMock />
        </div>
      </div>
    </section>
  );
}

function InterviewMock() {
  return (
    <div className="space-y-3">
      {/* Session header */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 px-5 py-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-lg bg-indigo-600 grid place-items-center shadow-sm">
              <Mic className="w-3.5 h-3.5 text-white" />
            </span>
            <span className="text-[13px] font-semibold text-gray-900">AI Mock Interview</span>
          </div>
          <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-full bg-red-50 ring-1 ring-red-200 text-red-700">
            Hard
          </span>
        </div>
        <div className="flex items-center justify-between mb-1.5 text-[11px] text-gray-400">
          <span>Question 3 of 7</span>
          <span>System Design</span>
        </div>
        <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
            style={{ width: "42%" }}
          />
        </div>
      </div>

      {/* Question card */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center gap-2">
          <AudioLines className="w-3.5 h-3.5 text-indigo-500" />
          <span className="text-[12px] font-semibold text-gray-900">AI is asking…</span>
        </div>
        <div className="px-4 py-3.5">
          <p className="text-[13px] text-gray-800 leading-relaxed">
            &ldquo;Design a URL shortener like bit.ly. Walk me through the system
            components, how you&apos;d handle 100M daily redirects, and the trade-offs
            for consistency vs. availability.&rdquo;
          </p>
        </div>
        <div className="px-4 pb-3 flex items-center gap-2">
          <div className="flex-1 rounded-lg bg-red-50 ring-1 ring-red-200 px-3 py-1.5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[11.5px] text-red-700 font-medium">Recording answer…</span>
          </div>
        </div>
      </div>

      {/* Report preview */}
      <div className="rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 border-b border-gray-100 flex items-center gap-2">
          <Trophy className="w-3.5 h-3.5 text-amber-500" />
          <span className="text-[12px] font-semibold text-gray-900">Session Report</span>
          <span className="ml-auto text-[11px] font-bold text-emerald-600">74 / 100</span>
        </div>
        <div className="px-4 py-3 space-y-2.5">
          {[
            { label: "Communication",   score: 85, color: "bg-emerald-500" },
            { label: "Technical Depth", score: 72, color: "bg-blue-500" },
            { label: "Problem Solving", score: 68, color: "bg-amber-500" },
          ].map((s) => (
            <div key={s.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11.5px] text-gray-700">{s.label}</span>
                <span className="text-[11px] font-semibold text-gray-900">{s.score}</span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div className={`h-full rounded-full ${s.color}`} style={{ width: `${s.score}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className="px-4 pb-3 pt-1">
          <div className="rounded-lg bg-emerald-50 ring-1 ring-emerald-200 px-3 py-2 text-[11.5px] text-emerald-700 leading-snug">
            <span className="font-semibold">Feedback:</span> Good coverage of load balancing and hashing but missed discussing database sharding and cache invalidation strategies.
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── HOW IT WORKS ────────────────────────────────────────────────────── */

function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "Track every application and contact",
      body: "Add each role in under 30 seconds. Log every referral contact the moment you send a LinkedIn invite. Drop your resume and JD for AI-personalized follow-ups.",
    },
    {
      n: "02",
      title: "Jarvis tells you what to do today",
      body: "Open the app or speak to Jarvis — by chat or voice. It surfaces your 3–5 highest-priority actions, drafts follow-ups on demand, and updates your tracker when you're done.",
    },
    {
      n: "03",
      title: "Study, follow up, earn XP. Repeat.",
      body: "Work your daily quests, build your streak, tick off study topics. Every action earns XP. Jarvis keeps you consistent until an offer lands.",
    },
  ];

  return (
    <section id="how-it-works" className="py-24 bg-gray-50 border-y border-gray-100">
      <div className="max-w-6xl mx-auto px-6">
        <div className="max-w-2xl">
          <div className="text-[12px] font-semibold uppercase tracking-wider text-indigo-600 mb-2">
            How it works
          </div>
          <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
            From chaos to a clear<br />daily checklist.
          </h2>
        </div>
        <div className="mt-12 grid md:grid-cols-3 gap-4">
          {steps.map((s, i) => (
            <div
              key={s.n}
              className="relative rounded-2xl bg-white ring-1 ring-gray-200 p-6 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="font-mono text-[12px] text-indigo-600 font-semibold">
                  {s.n}
                </span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
              <div className="text-[18px] font-semibold text-gray-900 mb-2">
                {s.title}
              </div>
              <p className="text-[13.5px] text-gray-600 leading-relaxed">{s.body}</p>
              {i < steps.length - 1 ? (
                <ChevronRight
                  aria-hidden
                  className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-300 bg-gray-50 rounded-full"
                />
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── COMPARISON ──────────────────────────────────────────────────────── */

function Comparison() {
  const rows = [
    { feature: "Kanban application pipeline",         spreadsheet: false, trello: true,  githired: true },
    { feature: "Referral pipeline tracking",          spreadsheet: false, trello: false, githired: true },
    { feature: "Tells you exactly what to do today",  spreadsheet: false, trello: false, githired: true },
    { feature: "AI-drafted follow-ups & referral asks", spreadsheet: false, trello: false, githired: true },
    { feature: "AI-generated study plan",             spreadsheet: false, trello: false, githired: true },
    { feature: "DSA problem log + AI code review",   spreadsheet: false, trello: false, githired: true },
    { feature: "XP, streaks & achievements",          spreadsheet: false, trello: false, githired: true },
    { feature: "Voice agent — hands-free updates",    spreadsheet: false, trello: false, githired: true },
    { feature: "ATS resume scoring (ML-powered)",     spreadsheet: false, trello: false, githired: true },
    { feature: "AI mock interview + scored report",   spreadsheet: false, trello: false, githired: true },
    { feature: "Decays after week 2",                 spreadsheet: true,  trello: false, githired: false },
  ];

  return (
    <section id="why" className="py-24 border-y border-gray-100">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto">
          <div className="text-[12px] font-semibold uppercase tracking-wider text-indigo-600 mb-2">
            Why GitHired
          </div>
          <h2 className="text-[34px] sm:text-[40px] font-bold tracking-tight text-gray-900 leading-tight">
            Spreadsheets show what <em>exists</em>.<br />
            <span className="text-indigo-600">GitHired tells you what matters today.</span>
          </h2>
        </div>

        <div className="mt-12 rounded-2xl bg-white ring-1 ring-gray-200 overflow-hidden shadow-sm">
          <table className="w-full text-[14px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-5 py-3 font-medium text-gray-600">Capability</th>
                <th className="text-center px-3 py-3 font-medium text-gray-500">Spreadsheet</th>
                <th className="text-center px-3 py-3 font-medium text-gray-500">Trello / Notion</th>
                <th className="text-center px-3 py-3 font-medium text-indigo-700">
                  <span className="inline-flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5" />
                    GitHired
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.feature} className={i % 2 ? "bg-gray-50/50" : ""}>
                  <td className="px-5 py-3 text-gray-800">{r.feature}</td>
                  <td className="px-3 py-3 text-center">
                    {r.spreadsheet ? <Tick /> : <Dash />}
                  </td>
                  <td className="px-3 py-3 text-center">
                    {r.trello ? <Tick /> : <Dash />}
                  </td>
                  <td className="px-3 py-3 text-center">
                    {r.githired ? <Tick /> : <Dash />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

const Tick = () => (
  <CheckCircle2 className="inline text-emerald-500" style={{ width: 18, height: 18 }} />
);
const Cross = () => <span className="inline-block text-red-400">✕</span>;
const Dash = () => <span className="inline-block text-gray-300">—</span>;

/* ── FINAL CTA ───────────────────────────────────────────────────────── */

function FinalCTA() {
  return (
    <section className="py-24">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <div className="inline-grid place-items-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white mb-6 shadow-lg">
          <Sparkles className="w-7 h-7" />
        </div>
        <h2 className="text-[34px] sm:text-[44px] font-bold tracking-tight text-gray-900 leading-tight">
          Ready to run your job hunt like a pro?
        </h2>
        <p className="mt-4 text-[16px] text-gray-600 max-w-xl mx-auto">
          Track applications, score your resume against any JD, study with AI,
          practice real interview questions by voice, earn XP for every action,
          and let Jarvis keep you on track. Sign in free and start today.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-6 h-12 font-medium text-[15px] shadow-sm transition-colors"
          >
            Sign in with Google — it&apos;s free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="mt-6 flex items-center justify-center gap-6 text-[13px] text-gray-400">
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            No credit card
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            Google sign-in
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            Built for junior devs
          </span>
        </div>
      </div>
    </section>
  );
}

/* ── FOOTER ──────────────────────────────────────────────────────────── */

function Footer() {
  return (
    <footer className="border-t border-gray-200 py-10 bg-white">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[13px] text-gray-500">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded-md bg-indigo-600 text-white grid place-items-center">
            <Briefcase className="w-3.5 h-3.5" />
          </span>
          <span className="font-semibold text-gray-700">GitHired</span>
          <span>· built by Atharva Jamdar</span>
        </div>
        <div className="flex items-center gap-5">
          <a href="#track" className="hover:text-gray-900">Track</a>
          <a href="#learn" className="hover:text-gray-900">Learn</a>
          <a href="#practice" className="hover:text-gray-900">Practice</a>
          <a href="#motivate" className="hover:text-gray-900">Motivate</a>
          <a href="#ats" className="hover:text-gray-900">ATS</a>
          <a href="#interview" className="hover:text-gray-900">Interview</a>
          <Link href="/login" className="hover:text-gray-900">Sign in</Link>
        </div>
        <div className="text-gray-400">© {new Date().getFullYear()}</div>
      </div>
    </footer>
  );
}

/* ── SHARED COMPONENTS ───────────────────────────────────────────────── */

function PillarLabel({
  color,
  n,
  label,
}: {
  color: string;
  n: string;
  label: string;
}) {
  return (
    <div className={`flex items-center gap-2 text-[12px] font-semibold uppercase tracking-wider ${color}`}>
      <span className="font-mono">{n}</span>
      <span className="w-8 h-px bg-current opacity-40" />
      <span>{label}</span>
    </div>
  );
}

const toneMap: Record<string, { icon: string; card: string }> = {
  orange: { icon: "bg-orange-50 text-orange-600", card: "border-orange-100" },
  emerald: { icon: "bg-emerald-50 text-emerald-600", card: "border-emerald-100" },
  blue: { icon: "bg-blue-50 text-blue-600", card: "border-blue-100" },
  violet: { icon: "bg-violet-50 text-violet-600", card: "border-violet-100" },
  rose: { icon: "bg-rose-50 text-rose-600", card: "border-rose-100" },
  indigo: { icon: "bg-indigo-50 text-indigo-600", card: "border-indigo-100" },
};

function FeatureCard({
  icon,
  tone,
  title,
  body,
}: {
  icon: ReactNode;
  tone: "orange" | "emerald" | "blue" | "violet" | "rose" | "indigo";
  title: string;
  body: string;
}) {
  const t = toneMap[tone];
  return (
    <div className={`rounded-xl bg-white ring-1 ring-gray-200 p-4 shadow-sm border-b-2 ${t.card}`}>
      <span className={`inline-grid place-items-center w-9 h-9 rounded-lg mb-3 ${t.icon}`}>
        {icon}
      </span>
      <div className="text-[14px] font-semibold text-gray-900 mb-1">{title}</div>
      <p className="text-[12.5px] text-gray-600 leading-relaxed">{body}</p>
    </div>
  );
}

function MockColumn({
  status,
  color,
  cards,
}: {
  status: string;
  color: string;
  cards: { co: string; role: string; days: number }[];
}) {
  return (
    <div className="rounded-xl bg-gray-50 ring-1 ring-gray-200 overflow-hidden">
      <div className={`h-1 ${color}`} />
      <div className="px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
          <span className="text-[11.5px] font-semibold text-gray-800">{status}</span>
        </div>
        <span className="text-[10px] text-gray-500 bg-white ring-1 ring-gray-200 rounded-full px-1.5 py-0.5">
          {cards.length}
        </span>
      </div>
      <div className="px-2 pb-2 space-y-1.5">
        {cards.map((c) => (
          <div key={c.co} className="rounded-md bg-white ring-1 ring-gray-200 p-2">
            <div className="text-[11.5px] font-semibold text-gray-900 truncate">{c.co}</div>
            <div className="text-[10px] text-gray-500 truncate">{c.role}</div>
            <div className="text-[9.5px] text-gray-400 mt-1">{c.days}d ago</div>
          </div>
        ))}
      </div>
    </div>
  );
}

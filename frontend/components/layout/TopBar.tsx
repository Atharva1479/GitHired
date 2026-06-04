"use client";

import {
  Bell,
  BookOpenCheck,
  BrainCircuit,
  Briefcase,
  ChevronDown,
  FileText,
  LogOut,
  Mic,
  ScanText,
  Settings,
  Trophy,
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { StreakFlame } from "@/components/gamify/StreakFlame";
import { XpBar } from "@/components/gamify/XpBar";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useLogout, useMe } from "@/hooks/useMe";
import { useTodayNudges } from "@/hooks/useNudges";
import { sfx } from "@/lib/sfx";

const PREP_ITEMS = [
  { href: "/study",     icon: BookOpenCheck, label: "Study",     desc: "Flashcards & plans" },
  { href: "/dsa",       icon: BrainCircuit,  label: "DSA",       desc: "Algorithm practice" },
  { href: "/ats",       icon: ScanText,      label: "ATS",       desc: "Resume scanner" },
  { href: "/resumes",   icon: FileText,      label: "Skill Gap",  desc: "Resume & gap analysis" },
  { href: "/interview", icon: Mic,           label: "Interview", desc: "AI mock interviews" },
];

function PrepDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={ref}
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-[13.5px] transition-colors hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] ${
          open ? "bg-[var(--color-surface-2)] text-[var(--color-text)]" : "text-[var(--color-text-2)]"
        }`}
      >
        Prep
        <ChevronDown
          className={`w-3.5 h-3.5 opacity-60 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-52 rounded-xl bg-[var(--color-surface)] shadow-xl ring-1 ring-[var(--color-border)] py-1.5 z-50 fade-up">
          {PREP_ITEMS.map(({ href, icon: Icon, label, desc }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
              onClick={() => setOpen(false)}
            >
              <span className="shrink-0 w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                <Icon className="w-3.5 h-3.5 text-indigo-500" />
              </span>
              <span>
                <span className="block text-[13px] font-medium leading-tight">{label}</span>
                <span className="block text-[11px] text-[var(--color-text-3)] leading-tight mt-0.5">{desc}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function TopBar() {
  const today = useTodayNudges();
  const count = (today.data ?? []).length;

  return (
    <header className="sticky top-0 z-30 bg-[var(--color-surface)]/80 backdrop-blur border-b border-[var(--color-border)]">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2 group">
          <span className="w-7 h-7 rounded-lg bg-indigo-600 text-white grid place-items-center shadow-sm">
            <Briefcase className="w-4 h-4" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-[var(--color-text)] group-hover:text-[var(--color-primary)] transition-colors">
            GitHired
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-[13.5px] text-[var(--color-text-2)]">
          <Link
            href="/dashboard"
            className="px-3 py-1.5 rounded-md hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
          >
            Dashboard
          </Link>
          <Link
            href="/applications"
            className="px-3 py-1.5 rounded-md hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
          >
            Applications
          </Link>
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
          >
            <Zap className="w-4 h-4" />
            Jobs
          </Link>
          <Link
            href="/referrals"
            className="px-3 py-1.5 rounded-md hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
          >
            Referrals
          </Link>
          <PrepDropdown />
          <Link
            href="/nudges"
            className="relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
            aria-label={`Nudges${count ? ` (${count} pending)` : ""}`}
          >
            <Bell className="w-4 h-4" />
            <span>Nudges</span>
            {count > 0 ? (
              <span className="ml-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-indigo-600 text-white text-[10.5px] font-medium tabular-nums">
                {count > 99 ? "99+" : count}
              </span>
            ) : null}
          </Link>
          <span className="mx-1 h-5 w-px bg-[var(--color-border)]" aria-hidden />
          <StreakFlame />
          <XpBar />
          <ThemeToggle />
          <UserMenu />
        </nav>
      </div>
    </header>
  );
}

function UserMenu() {
  const { data: me } = useMe();
  const logout = useLogout();
  const [open, setOpen] = useState(false);
  const [soundOn, setSoundOn] = useState(true);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSoundOn(sfx.isEnabled());
    return sfx.subscribe(setSoundOn);
  }, []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (!me) return null;

  const initial = (me.display_name || me.email).charAt(0).toUpperCase();

  return (
    <div className="relative ml-1" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Account menu"
        className="flex items-center rounded-full ring-1 ring-[var(--color-border)] hover:ring-[var(--color-border-2)] transition-shadow"
      >
        {me.picture_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={me.picture_url}
            alt=""
            className="w-7 h-7 rounded-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <span className="w-7 h-7 rounded-full bg-indigo-600 text-white grid place-items-center text-[11.5px] font-semibold">
            {initial}
          </span>
        )}
      </button>

      {open ? (
        <div className="absolute right-0 mt-2 w-56 rounded-lg bg-[var(--color-surface)] shadow-lg ring-1 ring-[var(--color-border)] py-1.5 fade-up">
          <div className="px-3 py-2 border-b border-[var(--color-border)]">
            <p className="text-[13px] font-medium text-[var(--color-text)] truncate">
              {me.display_name}
            </p>
            <p className="text-[12px] text-[var(--color-text-3)] truncate">{me.email}</p>
          </div>
          <Link
            href="/settings"
            onClick={() => setOpen(false)}
            className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
          >
            <Settings className="w-3.5 h-3.5" />
            Settings
          </Link>
          <Link
            href="/achievements"
            onClick={() => setOpen(false)}
            className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
          >
            <Trophy className="w-3.5 h-3.5" />
            Achievements
          </Link>
          <button
            onClick={() => {
              sfx.unlock();
              sfx.setEnabled(!soundOn);
            }}
            className="w-full text-left flex items-center justify-between gap-2 px-3 py-2 text-[13px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
          >
            <span className="flex items-center gap-2">
              {soundOn ? (
                <Volume2 className="w-3.5 h-3.5" />
              ) : (
                <VolumeX className="w-3.5 h-3.5" />
              )}
              Sound FX
            </span>
            <span
              className={`text-[10.5px] font-bold tracking-wider uppercase px-1.5 rounded-full ${
                soundOn
                  ? "bg-emerald-500/10 text-emerald-600"
                  : "bg-[var(--color-surface-2)] text-[var(--color-text-3)]"
              }`}
            >
              {soundOn ? "On" : "Off"}
            </span>
          </button>
          <button
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            className="w-full text-left flex items-center gap-2 px-3 py-2 text-[13px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] disabled:opacity-60 border-t border-[var(--color-border)]"
          >
            <LogOut className="w-3.5 h-3.5" />
            {logout.isPending ? "Signing out…" : "Sign out"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

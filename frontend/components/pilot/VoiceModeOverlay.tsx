"use client";

import { Settings2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useMe } from "@/hooks/useMe";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { api } from "@/lib/api";

import { VoicePearl } from "./VoicePearl";

/**
 * Voice mode is intentionally chrome-less: just the morphing pearl
 * floating at the bottom-right corner of the page. Click the pearl to
 * start listening, click again to stop, click while Pilot is speaking
 * to interrupt. A tiny X appears on hover so the user can close.
 *
 * The pearl is mounted in <AppShell />, so it persists across all route
 * changes without interrupting the conversation.
 */
export function VoiceModeOverlay({
  open,
  agent,
  onClose,
}: {
  open: boolean;
  agent: ReturnType<typeof useVoiceAgent>;
  onClose: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (menuOpen) {
          setMenuOpen(false);
          return;
        }
        agent.cancel();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, agent, onClose, menuOpen]);

  // Outside-click close for the settings menu.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  if (!open) return null;

  const handlePearlClick = () => {
    if (agent.status === "idle") {
      agent.startRecording();
    } else if (agent.status === "recording") {
      agent.stopRecording();
    }
    // While Pilot is speaking / thinking / transcribing we intentionally
    // do nothing on a click. Previously a tap during "speaking" called
    // cancel(), which both interrupted Pilot AND triggered continuous-
    // listen 350ms later — a single click did two unintended things.
    //
    // The user can still interrupt naturally by:
    //   - speaking (barge-in detector cancels TTS for them)
    //   - pressing Esc / hitting the X to close voice mode
    //
    // After Pilot finishes, continuous-listen re-arms the mic
    // automatically, so the click here is never needed.
  };

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Jarvis voice mode"
      className="group/pearl fixed bottom-6 right-6 z-[80] fade-up"
    >
      <VoicePearl
        status={agent.status}
        amplitude={agent.amplitude}
        size={132}
        onClick={handlePearlClick}
      />

      {/* Settings — revealed on hover. */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen((o) => !o);
        }}
        aria-label="Voice settings"
        aria-expanded={menuOpen}
        className="absolute -top-1 left-0 grid place-items-center w-7 h-7 rounded-full bg-slate-900/75 text-white/85 ring-1 ring-white/15 backdrop-blur-md opacity-0 group-hover/pearl:opacity-100 transition-opacity duration-150 shadow-lg"
      >
        <Settings2 className="w-3.5 h-3.5" />
      </button>

      {/* Close — revealed on hover only. No persistent chrome. */}
      <button
        type="button"
        onClick={() => {
          agent.cancel();
          onClose();
        }}
        aria-label="Close voice mode"
        className="absolute -top-1 -right-1 grid place-items-center w-7 h-7 rounded-full bg-slate-900/75 text-white/85 ring-1 ring-white/15 backdrop-blur-md opacity-0 group-hover/pearl:opacity-100 transition-opacity duration-150 shadow-lg"
      >
        <X className="w-3.5 h-3.5" />
      </button>

      {menuOpen ? (
        <SettingsMenu ref={menuRef} agent={agent} onClose={() => setMenuOpen(false)} />
      ) : null}

      {agent.error ? (
        <div
          className="absolute -top-10 right-0 max-w-[240px] text-[11.5px] text-rose-100 px-2.5 py-1.5 rounded-lg bg-rose-600/70 backdrop-blur-sm ring-1 ring-rose-300/20"
          role="alert"
        >
          {agent.error}
        </div>
      ) : null}
    </div>
  );
}

const SettingsMenu = function SettingsMenu({
  ref,
  agent,
  onClose,
}: {
  ref: React.RefObject<HTMLDivElement | null>;
  agent: ReturnType<typeof useVoiceAgent>;
  onClose: () => void;
}) {
  const { data: me, refetch } = useMe();
  const [savingBrief, setSavingBrief] = useState(false);
  const briefOn = me?.auto_brief_enabled ?? false;

  const toggleBrief = async () => {
    setSavingBrief(true);
    try {
      await api.auth.updatePreferences({ auto_brief_enabled: !briefOn });
      await refetch();
    } finally {
      setSavingBrief(false);
    }
  };

  return (
    <div
      ref={ref}
      role="menu"
      className="absolute bottom-[140px] right-0 w-[240px] rounded-2xl bg-slate-900/85 text-white ring-1 ring-white/10 backdrop-blur-xl shadow-2xl fade-up p-2"
    >
      <div className="px-2 pt-1 pb-2 text-[10.5px] uppercase tracking-[0.2em] text-white/55">
        Jarvis · voice settings
      </div>
      <ToggleRow
        label="Continuous listening"
        sub="Re-arm the mic after Jarvis replies"
        on={agent.continuousMode}
        onToggle={() => agent.setContinuousMode(!agent.continuousMode)}
      />
      <ToggleRow
        label="Interrupt on speak"
        sub="Cut Jarvis off when you start talking"
        on={agent.bargeInEnabled}
        onToggle={() => agent.setBargeInEnabled(!agent.bargeInEnabled)}
      />
      <ToggleRow
        label="Fast browser voice"
        sub="Lower latency, but ignores ELEVENLABS_VOICE_ID"
        on={agent.fastBrowserTts}
        onToggle={() => agent.setFastBrowserTts(!agent.fastBrowserTts)}
      />
      <ToggleRow
        label="Auto-greet on login"
        sub="Welcome you when you arrive"
        on={briefOn}
        disabled={savingBrief}
        onToggle={toggleBrief}
      />
      <ToggleRow
        label='Hey Jarvis wake word'
        sub='Always listen for "Hey Jarvis" to activate'
        on={agent.wakeWordEnabled}
        onToggle={() => agent.setWakeWordEnabled(!agent.wakeWordEnabled)}
      />
      <div className="my-1 border-t border-white/10" />
      <Link
        href="/pilot/history"
        onClick={onClose}
        className="block w-full text-left px-2.5 py-2 rounded-lg text-[12.5px] text-white/85 hover:text-white hover:bg-white/10 transition-colors"
        role="menuitem"
      >
        View conversation history →
      </Link>
    </div>
  );
};

function ToggleRow({
  label,
  sub,
  on,
  disabled,
  onToggle,
}: {
  label: string;
  sub: string;
  on: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      role="menuitemcheckbox"
      aria-checked={on}
      className="w-full flex items-center justify-between gap-3 px-2.5 py-2 rounded-lg hover:bg-white/10 transition-colors disabled:opacity-50"
    >
      <span className="text-left">
        <span className="block text-[12.5px] text-white/90">{label}</span>
        <span className="block text-[11px] text-white/45">{sub}</span>
      </span>
      <span
        aria-hidden
        className={`relative shrink-0 w-9 h-5 rounded-full transition-colors ${
          on ? "bg-indigo-500" : "bg-white/15"
        }`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${
            on ? "left-[18px]" : "left-0.5"
          }`}
        />
      </span>
    </button>
  );
}

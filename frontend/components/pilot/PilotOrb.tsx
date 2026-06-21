"use client";

import { AudioLines, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useGamifyState } from "@/hooks/useGamify";
import { useMe } from "@/hooks/useMe";
import { useSettings } from "@/hooks/useSettings";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { useWakeWord } from "@/hooks/useWakeWord";
import { api } from "@/lib/api";

import { PilotPanel } from "./PilotPanel";
import { VoiceModeOverlay } from "./VoiceModeOverlay";

// Unlock audio on the first user gesture, then call the pending callback.
// Chrome blocks AudioContext.resume() / audio.play() until the user has
// interacted with the page at least once; this defers the auto-greet until
// that first pointer-down or key-down without requiring a dedicated button.
function useGestureUnlock(callback: (() => void) | null) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!callback) return;
    let fired = false;

    const fire = () => {
      if (fired) return;
      fired = true;
      document.removeEventListener("pointerdown", fire, { capture: true });
      document.removeEventListener("keydown", fire, { capture: true });
      cbRef.current?.();
    };

    document.addEventListener("pointerdown", fire, { capture: true });
    document.addEventListener("keydown", fire, { capture: true });
    return () => {
      document.removeEventListener("pointerdown", fire, { capture: true });
      document.removeEventListener("keydown", fire, { capture: true });
    };
  }, [callback]);
}

// How long (ms) the agent can sit idle in voice mode before auto-closing.
// Resets whenever the agent starts recording, thinking, or speaking.
const WAKE_IDLE_TIMEOUT_MS = 15_000;

const _SESSION_GREETED_KEY = "jp_pilot_greeted_at";
// localStorage key holding the last session_id we already greeted for.
// localStorage (not sessionStorage) is correct here: we want the value
// to survive page refresh, browser restart, even tab close. The greet
// happens once per *login*, full stop — anything else (refresh,
// re-open tab) compares the persisted id against me.session_id and
// stays silent if they match.
const _WELCOMED_SID_KEY = "jp_pilot_welcomed_sid";

function buildWelcome(firstName: string): string {
  return (
    `Welcome back, ${firstName}. Let's keep the job hunt moving — ` +
    `tell me what you want to work on, or ask anything about where you stand.`
  );
}

export function PilotOrb() {
  const [panelOpen, setPanelOpen] = useState(false);
  // Voice mode auto-opens once per session (see effect below). Closing
  // it explicitly is sticky for the rest of the session.
  const [voiceMode, setVoiceMode] = useState(false);
  const [greeting, setGreeting] = useState<string | null>(null);
  // Text to speak once the user makes their first gesture (pointer / key).
  // Chrome blocks AudioContext / audio.play() without a prior user gesture,
  // so we can't call greetWithMessage() the moment /me resolves on login.
  const [pendingGreet, setPendingGreet] = useState<string | null>(null);
  const { data: state }    = useGamifyState();
  const { data: me }       = useMe();
  const { data: settings } = useSettings();

  // Single agent state shared by chat panel + voice overlay so the
  // conversation continues if the user switches surfaces mid-session.
  const agent = useVoiceAgent();
  const greetingSpokenRef = useRef(false);
  const welcomedRef = useRef(false);
  const idleTimerRef = useRef<number | null>(null);

  // Fetch a fresh greeting once per session (kept for the chat panel
  // intro pill; the voice welcome uses a different copy below).
  useEffect(() => {
    let cancelled = false;
    const today = new Date().toISOString().slice(0, 10);
    let last = "";
    try {
      last = sessionStorage.getItem(_SESSION_GREETED_KEY) || "";
    } catch {}
    if (last === today) return;
    (async () => {
      try {
        const { text } = await api.pilot.greeting();
        if (!cancelled) {
          setGreeting(text);
          try {
            sessionStorage.setItem(_SESSION_GREETED_KEY, today);
          } catch {}
        }
      } catch {
        // pilot not configured / disabled — silent fall-through
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Greet the user exactly once per LOGIN (not per refresh, not per
  // session, not per day). We compare `me.session_id` — a UUID baked
  // into the signed session cookie at login — against the last sid we
  // greeted for. Refresh ⇒ same cookie ⇒ same sid ⇒ silent. Logout +
  // login ⇒ new cookie ⇒ new sid ⇒ greet.
  useEffect(() => {
    if (welcomedRef.current) return;
    if (!me) return;
    // Respect the opt-out. The toggle lives in the voice settings menu.
    if (me.auto_brief_enabled === false) {
      welcomedRef.current = true;
      return;
    }
    const sid = me.session_id;
    if (!sid) {
      // Older session cookie from before this feature shipped — stay
      // quiet. Next real login will issue a sid and greet then.
      welcomedRef.current = true;
      return;
    }
    let lastGreetedSid = "";
    try {
      lastGreetedSid = localStorage.getItem(_WELCOMED_SID_KEY) || "";
    } catch {}
    if (lastGreetedSid === sid) {
      welcomedRef.current = true;
      return;
    }
    welcomedRef.current = true;
    try {
      localStorage.setItem(_WELCOMED_SID_KEY, sid);
    } catch {}
    const firstName = (me.display_name ?? "").split(" ")[0] || "there";
    setVoiceMode(true);
    greetingSpokenRef.current = true;
    // Don't call greetWithMessage() here — Chrome blocks audio without a
    // prior user gesture. Store the text and fire on the first gesture.
    setPendingGreet(buildWelcome(firstName));
  }, [me]);

  // Play the pending greeting on the first user gesture (pointer / key).
  // Captures at the document level so any tap — including the pearl — fires it.
  useGestureUnlock(
    pendingGreet
      ? () => {
          const text = pendingGreet;
          setPendingGreet(null);
          agent.greetWithMessage(text, { fastTts: true });
        }
      : null,
  );

  // Discard pending greeting if the user closes voice mode before touching anything.
  useEffect(() => {
    if (!voiceMode) setPendingGreet(null);
  }, [voiceMode]);

  // 15 s idle-shutdown: while voice mode is open, if the agent stays
  // "idle" (not recording / thinking / speaking) for 15 s we close voice
  // mode so the mic isn't left hot indefinitely. The timer resets whenever
  // the agent transitions out of idle.
  useEffect(() => {
    if (!voiceMode) {
      if (idleTimerRef.current !== null) {
        clearTimeout(idleTimerRef.current);
        idleTimerRef.current = null;
      }
      return;
    }
    if (agent.status === "idle") {
      if (idleTimerRef.current === null) {
        idleTimerRef.current = window.setTimeout(() => {
          idleTimerRef.current = null;
          setVoiceMode(false);
        }, WAKE_IDLE_TIMEOUT_MS);
      }
    } else {
      if (idleTimerRef.current !== null) {
        clearTimeout(idleTimerRef.current);
        idleTimerRef.current = null;
      }
    }
  }, [voiceMode, agent.status]);

  // Activated by the "Jarvis" / "Hey Jarvis" wake word. Opens voice mode
  // and starts listening immediately — no greeting replayed.
  const activateByWakeWord = useCallback(() => {
    setPanelOpen(false);
    setVoiceMode(true);
    greetingSpokenRef.current = true; // skip the welcome speech
    void agent.startRecording();
  }, [agent]);

  // Wake word detection: enabled only when voice mode is closed AND the user
  // hasn't turned it off in Settings. Falls back to enabled when settings
  // haven't loaded yet (undefined) so the feature is on by default.
  const wakeWordEnabled = !voiceMode && agent.wakeWordEnabled;
  const { supported: wakeWordSupported } = useWakeWord({
    enabled: wakeWordEnabled,
    onTrigger: activateByWakeWord,
    restartDelay: 2000,
  });

  const level = state?.level ?? 1;

  const openVoiceMode = () => {
    setPanelOpen(false);
    setVoiceMode(true);
    // Greet only if this login session hasn't been greeted yet.
    // Check localStorage (persists across refreshes) not the in-memory ref.
    const sid = me?.session_id;
    let alreadyGreeted = false;
    try {
      alreadyGreeted = !!sid && localStorage.getItem(_WELCOMED_SID_KEY) === sid;
    } catch {}
    if (!alreadyGreeted) {
      greetingSpokenRef.current = true;
      if (sid) {
        try { localStorage.setItem(_WELCOMED_SID_KEY, sid); } catch {}
      }
      const firstName = (me?.display_name ?? "").split(" ")[0] || "there";
      agent.greetWithMessage(buildWelcome(firstName), { fastTts: true });
    }
  };

  return (
    <>
      <div
        className={`group fixed bottom-6 right-6 z-40 flex items-center gap-2 transition-opacity duration-200 ${
          voiceMode ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        {/* Hover-revealed Voice mode button. Always shown on touch. */}
        <button
          type="button"
          onClick={openVoiceMode}
          aria-label="Open voice mode"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-gray-900 text-white text-[12px] font-medium shadow-lg ring-1 ring-white/10 opacity-0 translate-x-2 transition-all duration-200 hover:bg-gray-800 focus-visible:opacity-100 focus-visible:translate-x-0 group-hover:opacity-100 group-hover:translate-x-0 [@media(hover:none)]:opacity-100 [@media(hover:none)]:translate-x-0"
        >
          <AudioLines className="w-3.5 h-3.5" />
          <span>Voice</span>
        </button>

        <button
          type="button"
          onClick={() => setPanelOpen(true)}
          aria-label="Open Jarvis"
          className="relative flex items-center gap-2"
        >
          {greeting && !panelOpen && !voiceMode ? (
            <span className="hidden sm:block max-w-[260px] truncate rounded-full bg-gray-900 text-white text-[12.5px] px-3 py-1.5 shadow-lg fade-up">
              {greeting}
            </span>
          ) : null}
          <span className="relative grid place-items-center w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-white shadow-[0_8px_30px_rgba(99,102,241,0.45)] hover:shadow-[0_10px_36px_rgba(99,102,241,0.55)] transition-shadow">
            <span className="absolute inset-0 rounded-full bg-white/10 animate-ping opacity-70" />
            <Sparkles className="w-6 h-6 relative" />
            <span className="absolute -bottom-1 -right-1 grid place-items-center w-5 h-5 rounded-full bg-white text-indigo-700 text-[10.5px] font-bold ring-2 ring-white shadow">
              {level}
            </span>
            {/* Wake-word listening indicator */}
            {wakeWordEnabled && wakeWordSupported && (
              <span
                title='Listening for "Hey Jarvis"'
                className="absolute -top-0.5 -left-0.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-white animate-pulse"
              />
            )}
          </span>
        </button>
      </div>

      <PilotPanel
        agent={agent}
        open={panelOpen}
        greeting={greeting}
        onClose={() => setPanelOpen(false)}
        onOpenVoiceMode={openVoiceMode}
      />

      <VoiceModeOverlay
        open={voiceMode}
        agent={agent}
        onClose={() => setVoiceMode(false)}
      />
    </>
  );
}

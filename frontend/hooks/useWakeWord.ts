"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Primary phrase + common phonetic misrecognitions Chrome STT returns for
// "Jarvis" (a proper noun it doesn't always spell correctly).
const WAKE_PHRASES = [
  "jarvis",
  "hey jarvis",
  "ok jarvis",
  "hi jarvis",
  // Chrome STT phonetic misses for "Jarvis":
  "garvis",
  "harvis",
  "jarvas",
  "jarvice",
  "harvest",   // rare but heard
];

// Minimal inline types for the Web Speech API (not in standard TS dom lib).
type SRResult = { transcript: string; confidence: number };
type SRResultList = { length: number; isFinal: boolean } & ArrayLike<SRResult>;
type SREvent = { resultIndex: number; results: ArrayLike<SRResultList> };
type SRErrorEvent = { error: string };
type SR = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart:  (() => void) | null;
  onresult: ((e: SREvent) => void) | null;
  onend:    (() => void) | null;
  onerror:  ((e: SRErrorEvent) => void) | null;
  start():  void;
  abort():  void;
};
type SRCtor = new () => SR;

function getSR(): SRCtor | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { SpeechRecognition?: SRCtor }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: SRCtor })
      .webkitSpeechRecognition ??
    null
  );
}

export type WakeWordState = {
  /** True while SpeechRecognition is actively listening. */
  listening: boolean;
  /** Set when mic permission was denied — tells UI to show a hint. */
  micDenied: boolean;
};

/**
 * Always-on background listener for "Jarvis" / "Hey Jarvis".
 * Calls `onWake` when detected. Pass `enabled={false}` to pause while
 * the voice overlay has the mic.
 *
 * Returns `{ listening, micDenied }` so the UI can show status.
 */
export function useWakeWord(
  onWake: () => void,
  enabled: boolean,
): WakeWordState {
  const recognitionRef  = useRef<SR | null>(null);
  const onWakeRef       = useRef(onWake);
  onWakeRef.current     = onWake;
  const enabledRef      = useRef(enabled);
  enabledRef.current    = enabled;
  const restartTimerRef = useRef<number | null>(null);
  const genRef          = useRef(0);

  const [listening,  setListening]  = useState(false);
  const [micDenied,  setMicDenied]  = useState(false);

  const stop = useCallback(() => {
    genRef.current++;
    setListening(false);
    if (restartTimerRef.current !== null) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    const SR = getSR();
    if (!SR || !enabledRef.current) return;

    if (restartTimerRef.current !== null) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }

    const gen = ++genRef.current;

    const scheduleRestart = (delayMs: number) => {
      setListening(false);
      if (genRef.current !== gen || !enabledRef.current) return;
      restartTimerRef.current = window.setTimeout(() => {
        restartTimerRef.current = null;
        if (enabledRef.current && genRef.current === gen) start();
      }, delayMs);
    };

    const recognition = new SR();
    recognition.continuous      = true;
    recognition.interimResults  = true;
    recognition.lang            = "en-US";
    recognition.maxAlternatives = 5;

    recognition.onstart = () => {
      if (genRef.current !== gen) return;
      setListening(true);
      setMicDenied(false);
    };

    recognition.onresult = (event: SREvent) => {
      if (!enabledRef.current || genRef.current !== gen) return;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        for (let j = 0; j < res.length; j++) {
          const t = res[j].transcript.trim().toLowerCase();
          if (WAKE_PHRASES.some((p) => t.includes(p))) {
            onWakeRef.current();
            return;
          }
        }
      }
    };

    recognition.onend = () => {
      if (genRef.current !== gen) return;
      recognitionRef.current = null;
      if (!enabledRef.current) return;
      scheduleRestart(300);
    };

    recognition.onerror = (event: SRErrorEvent) => {
      if (genRef.current !== gen || event.error === "aborted") return;
      recognitionRef.current = null;
      if (!enabledRef.current) return;

      if (event.error === "not-allowed") {
        setMicDenied(true);
        setListening(false);
        return; // don't retry — user needs to grant permission
      }
      scheduleRestart(event.error === "no-speech" ? 300 : 3000);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch {
      recognitionRef.current = null;
      scheduleRestart(1000);
    }
  }, []); // all deps via refs

  useEffect(() => {
    if (enabled) {
      const initTimer = window.setTimeout(start, 500);
      return () => {
        clearTimeout(initTimer);
        stop();
      };
    } else {
      stop();
    }
  }, [enabled, start, stop]);

  return { listening, micDenied };
}

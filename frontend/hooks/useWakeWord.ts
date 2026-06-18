"use client";

import { useCallback, useEffect, useRef } from "react";

export interface WakeWordOptions {
  enabled: boolean;        // Toggle listening on/off
  onTrigger: () => void;   // Called when wake word detected
  restartDelay?: number;   // ms before re-arming after trigger (default 2000)
}

export interface WakeWordState {
  supported: boolean;  // Whether browser supports Web Speech API
}

// Wake words to detect (case-insensitive)
const WAKE_PHRASES = ["jarvis", "hey jarvis", "ok jarvis"];

// Minimal inline types for the Web Speech API
type SRResult = { transcript: string; confidence: number };
type SRResultList = { length: number; isFinal: boolean } & ArrayLike<SRResult>;
type SREvent = { resultIndex: number; results: ArrayLike<SRResultList> };
type SRErrorEvent = { error: string };
type SR = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onresult: ((e: SREvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: SRErrorEvent) => void) | null;
  start(): void;
  abort(): void;
};
type SRCtor = new () => SR;

function getSRCtor(): SRCtor | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { SpeechRecognition?: SRCtor }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: SRCtor })
      .webkitSpeechRecognition ??
    null
  );
}

export function useWakeWord(opts: WakeWordOptions): WakeWordState {
  const { enabled, onTrigger, restartDelay = 2000 } = opts;

  const SRCtor = getSRCtor();
  const supported = Boolean(SRCtor);

  const recognitionRef = useRef<SR | null>(null);
  const onTriggerRef = useRef(onTrigger);
  const enabledRef = useRef(enabled);
  const restartTimerRef = useRef<number | null>(null);
  const triggeredRef = useRef(false);

  // Keep refs synchronized with latest prop values
  useEffect(() => {
    onTriggerRef.current = onTrigger;
  }, [onTrigger]);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const start = useCallback(() => {
    if (!SRCtor || !enabledRef.current) return;

    // Clean up any pending restart
    if (restartTimerRef.current !== null) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }

    // Clean up old recognition instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }

    const recognition = new SRCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SREvent) => {
      if (!enabledRef.current || triggeredRef.current) return;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const resultList = event.results[i];
        for (let j = 0; j < resultList.length; j++) {
          const transcript = resultList[j].transcript
            .trim()
            .toLowerCase();

          // Check if any wake phrase matches
          if (
            WAKE_PHRASES.some((phrase) =>
              transcript.includes(phrase)
            )
          ) {
            // Trigger callback
            triggeredRef.current = true;
            onTriggerRef.current();

            // Stop recognition and restart after delay
            if (recognitionRef.current) {
              try {
                recognitionRef.current.abort();
              } catch {
                // ignore
              }
              recognitionRef.current = null;
            }

            // Re-arm after restartDelay
            restartTimerRef.current = window.setTimeout(() => {
              restartTimerRef.current = null;
              triggeredRef.current = false;
              if (enabledRef.current) {
                start();
              }
            }, restartDelay);

            return;
          }
        }
      }
    };

    recognition.onerror = (event: SRErrorEvent) => {
      recognitionRef.current = null;

      if (!enabledRef.current) return;

      // Auto-restart on certain errors with 500ms delay
      if (
        event.error === "no-speech" ||
        event.error === "aborted" ||
        event.error === "audio-capture"
      ) {
        if (restartTimerRef.current !== null) {
          clearTimeout(restartTimerRef.current);
        }
        restartTimerRef.current = window.setTimeout(() => {
          restartTimerRef.current = null;
          if (enabledRef.current) {
            start();
          }
        }, 500);
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;

      if (!enabledRef.current) return;

      // Auto-restart after browser stops recognition (200ms delay)
      if (restartTimerRef.current !== null) {
        clearTimeout(restartTimerRef.current);
      }
      restartTimerRef.current = window.setTimeout(() => {
        restartTimerRef.current = null;
        if (enabledRef.current) {
          start();
        }
      }, 200);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch {
      // If start() throws, restart after 500ms
      if (restartTimerRef.current !== null) {
        clearTimeout(restartTimerRef.current);
      }
      restartTimerRef.current = window.setTimeout(() => {
        restartTimerRef.current = null;
        if (enabledRef.current) {
          start();
        }
      }, 500);
    }
  }, [SRCtor, restartDelay]);

  useEffect(() => {
    if (enabled) {
      start();
    } else {
      // Stop recognition when disabled
      if (restartTimerRef.current !== null) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
        recognitionRef.current = null;
      }
    }

    return () => {
      // Cleanup on unmount
      if (restartTimerRef.current !== null) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
        recognitionRef.current = null;
      }
    };
  }, [enabled, start]);

  return { supported };
}

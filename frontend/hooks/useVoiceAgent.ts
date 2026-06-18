"use client";

import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  api,
  type PilotStreamEvent,
  type PilotToolTrace,
  type PilotTurn,
} from "@/lib/api";
import { keysForTrace } from "@/lib/voiceCacheKeys";

/**
 * Invalidate the React Query caches that the agent's writes affect.
 *
 * Called twice during a streaming turn: as soon as the SSE trace event
 * arrives (so list pages refresh while Pilot is still narrating the
 * result) and again from the non-streaming path when the response
 * lands. Idempotent — invalidateQueries is a no-op if the key isn't
 * currently observed by any mounted component.
 */
function _invalidateForTrace(
  qc: QueryClient,
  trace: readonly PilotToolTrace[] | undefined | null,
): void {
  if (!trace || trace.length === 0) return;
  const keys = keysForTrace(trace);
  for (const key of keys) {
    qc.invalidateQueries({ queryKey: key });
  }
}

export type AgentStatus =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "speaking";

export type AgentTurn = PilotTurn & {
  id: number;
  pending?: boolean;
  tool_trace?: PilotToolTrace[];
  outcome?: string;
};

const _STORAGE_KEY = "jp_pilot_voice_enabled";
const _CONTINUOUS_KEY = "jp_pilot_continuous_mode";
const _BARGE_IN_KEY = "jp_pilot_barge_in";
const _FAST_TTS_KEY = "jp_pilot_fast_browser_tts";
const _WAKE_WORD_KEY = "jp_pilot_wake_word";
const _AMPLITUDE_SMOOTH = 0.55; // weight of new sample (0–1); higher = snappier

// Silence-based auto-stop tuning. The user shouldn't have to click again
// to end a phrase — once they've clearly spoken (amplitude crossed
// VAD_SPEAK_THRESHOLD at least once), we end the recording after
// VAD_SILENCE_MS of continuous quiet.
const VAD_SPEAK_THRESHOLD = 0.10;   // must rise above this for voice to count
const VAD_SILENCE_THRESHOLD = 0.05; // below this is considered "silence"
// 2.0s gives slow speakers and people thinking mid-sentence enough room
// to pause without getting cut off. Anything under 1.5s cuts users off.
const VAD_SILENCE_MS = 2000;
const VAD_MIN_RECORD_MS = 500;      // never stop in the first half-second
// If the user opens the mic but never speaks, kill the recording after
// VAD_NO_SPEECH_TIMEOUT_MS so the mic doesn't stay live indefinitely.
// "Listening" feels broken if it just hangs there forever waiting.
const VAD_NO_SPEECH_TIMEOUT_MS = 8000;

// Barge-in tuning. While Pilot speaks we open a quiet mic just to watch
// for amplitude spikes. Threshold sits well above VAD's speak threshold
// so TTS speaker bleed-through can't false-trigger; the long debounce
// (300ms of sustained noise) keeps coughs / chair creaks / mouse clicks
// from interrupting; the warmup keeps the loudest part of TTS-bleed —
// the first half-second — out of detection scope entirely.
const BARGE_IN_THRESHOLD = 0.30;
const BARGE_IN_FRAMES = 18;          // ~300ms at 60fps — needs real speech
const BARGE_IN_WARMUP_MS = 600;      // ignore mic for first 600ms of TTS
const CONTINUOUS_RESUME_DELAY_MS = 350; // small breath between turns

// Audio constraints applied to every getUserMedia() in this hook —
// recording mic AND the barge-in watcher mic. Echo cancellation is the
// big one: it tells the browser to actively subtract speaker output
// from the mic signal so playback doesn't loop back as "user speech".
const _MIC_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

function pickMime(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg",
  ];
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c;
  }
  return "";
}

function extFromMime(mime: string): string {
  if (mime.startsWith("audio/webm")) return "webm";
  if (mime.startsWith("audio/mp4")) return "m4a";
  if (mime.startsWith("audio/ogg")) return "ogg";
  return "webm";
}

// Singleton AudioContext lazily created on first user gesture.
function getAudioContext(
  ref: React.MutableRefObject<AudioContext | null>,
): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (ref.current && ref.current.state !== "closed") return ref.current;
  const Ctor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext })
      .webkitAudioContext;
  if (!Ctor) return null;
  ref.current = new Ctor();
  return ref.current;
}

export function useVoiceAgent() {
  const queryClient = useQueryClient();
  const [history, setHistory] = useState<AgentTurn[]>([]);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    try {
      const v = window.localStorage.getItem(_STORAGE_KEY);
      return v === null ? true : v === "1";
    } catch {
      return true;
    }
  });
  const [continuousMode, setContinuousMode] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    try {
      const v = window.localStorage.getItem(_CONTINUOUS_KEY);
      return v === null ? true : v === "1";
    } catch {
      return true;
    }
  });
  const [bargeInEnabled, setBargeInEnabled] = useState<boolean>(() => {
    // Default OFF. Barge-in depends heavily on hardware (headphones vs
    // open speakers, mic quality, room acoustics). On open speakers it
    // false-fires constantly because TTS bleeds back into the mic and
    // the watcher treats Pilot's own voice as the user interrupting.
    // Users with headphones can opt in via the voice settings menu.
    if (typeof window === "undefined") return false;
    try {
      const v = window.localStorage.getItem(_BARGE_IN_KEY);
      return v === null ? false : v === "1";
    } catch {
      return false;
    }
  });
  // Default OFF: prefer ElevenLabs so the user's configured voice ID
  // is what they hear. Web Speech is sub-100ms latency but uses the
  // browser's default voice (often male on Windows) and ignores
  // ELEVENLABS_VOICE_ID entirely. Users can opt in via settings menu
  // if they care more about latency than voice quality.
  const [fastBrowserTts, setFastBrowserTts] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      const v = window.localStorage.getItem(_FAST_TTS_KEY);
      return v === null ? false : v === "1";
    } catch {
      return false;
    }
  });
  const [wakeWordEnabled, setWakeWordEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      const v = window.localStorage.getItem(_WAKE_WORD_KEY);
      return v === null ? false : v === "1";
    } catch {
      return false;
    }
  });
  const [amplitude, setAmplitude] = useState(0);
  const [interimUserText, setInterimUserText] = useState<string | null>(null);
  const idRef = useRef(1);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  // Audio analysis: one shared AudioContext, one AnalyserNode at a time.
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<AudioNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const bufferRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const smoothedRef = useRef(0);
  const ttsElementSourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  // VAD bookkeeping — only used while the analyser is wired to the mic.
  const vadStartedAtRef = useRef<number>(0);
  const vadLastVoiceAtRef = useRef<number>(0);
  const vadHasSpokenRef = useRef<boolean>(false);
  const vadAutoStopRef = useRef<(() => void) | null>(null);
  // Separate callback for the "no speech at all in N seconds" path —
  // unlike vadAutoStopRef, this one routes through cancel() (not just
  // stopRecording) so we DON'T send empty audio + don't auto-relisten.
  const vadNoSpeechCancelRef = useRef<(() => void) | null>(null);

  // Barge-in watcher refs. Lives only while Pilot is speaking — opens a
  // second mic stream just to detect "user is talking over Pilot".
  const bargeStreamRef = useRef<MediaStream | null>(null);
  const bargeAnalyserRef = useRef<AnalyserNode | null>(null);
  const bargeBufferRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const bargeRafRef = useRef<number | null>(null);
  const bargeTriggerCountRef = useRef<number>(0);

  // Continuous-mode + status refs so the TTS-end callbacks (which don't
  // see the latest state directly) can make the right call.
  const continuousModeRef = useRef<boolean>(continuousMode);
  continuousModeRef.current = continuousMode;
  const bargeInEnabledRef = useRef<boolean>(bargeInEnabled);
  bargeInEnabledRef.current = bargeInEnabled;
  const fastBrowserTtsRef = useRef<boolean>(fastBrowserTts);
  fastBrowserTtsRef.current = fastBrowserTts;
  // Set later, once startRecording is defined. The TTS-end callback
  // captures THIS ref, not the function, to break the dep cycle.
  const startRecordingRef = useRef<() => Promise<void>>(async () => {});
  const cancelTtsRef = useRef<() => void>(() => {});

  // When we programmatically end TTS (user click, voice-mode close,
  // overlapping new utterance), Web Speech still fires `utterance.onend`
  // — which would otherwise call _maybeContinueListening and re-arm the
  // mic, kicking off a recording the user never asked for. This ref
  // tells the next `onend` to skip the continuous-listen kick. The
  // timer self-clears after 200ms so a stale flag can never suppress a
  // legitimate later continue.
  const suppressContinueRef = useRef(false);
  const suppressContinueTimerRef = useRef<number | null>(null);

  // Persist voice toggle.
  useEffect(() => {
    try {
      localStorage.setItem(_STORAGE_KEY, voiceEnabled ? "1" : "0");
    } catch {}
  }, [voiceEnabled]);
  useEffect(() => {
    try {
      localStorage.setItem(_CONTINUOUS_KEY, continuousMode ? "1" : "0");
    } catch {}
  }, [continuousMode]);
  useEffect(() => {
    try {
      localStorage.setItem(_BARGE_IN_KEY, bargeInEnabled ? "1" : "0");
    } catch {}
  }, [bargeInEnabled]);
  useEffect(() => {
    try {
      localStorage.setItem(_FAST_TTS_KEY, fastBrowserTts ? "1" : "0");
    } catch {}
  }, [fastBrowserTts]);
  useEffect(() => {
    localStorage.setItem(_WAKE_WORD_KEY, wakeWordEnabled ? "1" : "0");
  }, [wakeWordEnabled]);

  const _appendTurn = useCallback(
    (turn: Omit<AgentTurn, "id">): AgentTurn => {
      const next: AgentTurn = { ...turn, id: idRef.current++ };
      setHistory((h) => [...h, next]);
      return next;
    },
    [],
  );

  const _stopAnalyser = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    try {
      sourceRef.current?.disconnect();
    } catch {}
    sourceRef.current = null;
    try {
      analyserRef.current?.disconnect();
    } catch {}
    analyserRef.current = null;
    bufferRef.current = null;
    smoothedRef.current = 0;
    vadAutoStopRef.current = null;
    vadNoSpeechCancelRef.current = null;
    vadHasSpokenRef.current = false;
    setAmplitude(0);
  }, []);

  const _startAnalyser = useCallback((source: AudioNode) => {
    const ctx = source.context as AudioContext;
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.4;
    source.connect(analyser);
    analyserRef.current = analyser;
    sourceRef.current = source;
    // Allocate against a fresh ArrayBuffer (not SharedArrayBuffer) so the
    // type matches AnalyserNode.getByteFrequencyData's expected param.
    bufferRef.current = new Uint8Array(
      new ArrayBuffer(analyser.frequencyBinCount),
    );

    const tick = () => {
      const a = analyserRef.current;
      const buf = bufferRef.current;
      if (!a || !buf) return;
      a.getByteFrequencyData(buf);
      // RMS-style mean, normalised to 0–1.
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length) / 255;
      // Soft compress so quiet voice still moves the orb, loud doesn't peg.
      const compressed = Math.min(1, Math.pow(rms, 0.7) * 1.6);
      smoothedRef.current =
        smoothedRef.current * (1 - _AMPLITUDE_SMOOTH) +
        compressed * _AMPLITUDE_SMOOTH;
      setAmplitude(smoothedRef.current);

      // Voice-activity detection (mic-only path). Two exit conditions:
      //  1. User spoke → silence for VAD_SILENCE_MS → auto-stop and send.
      //  2. User opened mic but never spoke for VAD_NO_SPEECH_TIMEOUT_MS
      //     → cancel entirely (don't send empty audio, don't leave mic
      //     hot indefinitely).
      const vadStop = vadAutoStopRef.current;
      if (vadStop) {
        const now = performance.now();
        if (smoothedRef.current >= VAD_SPEAK_THRESHOLD) {
          vadHasSpokenRef.current = true;
          vadLastVoiceAtRef.current = now;
        } else if (smoothedRef.current < VAD_SILENCE_THRESHOLD) {
          const recordedFor = now - vadStartedAtRef.current;
          const silentFor = now - vadLastVoiceAtRef.current;
          if (
            vadHasSpokenRef.current &&
            recordedFor >= VAD_MIN_RECORD_MS &&
            silentFor >= VAD_SILENCE_MS
          ) {
            // Latch off before calling — stopRecording cancels rAF.
            vadAutoStopRef.current = null;
            vadStop();
          }
        }
        // No-speech timeout: user hasn't said anything in N seconds —
        // abandon the recording. Falls through cancel() so the suppress-
        // continue flag fires too (we don't want continuous-listen to
        // re-arm the mic after we just decided nothing's there).
        if (
          !vadHasSpokenRef.current &&
          performance.now() - vadStartedAtRef.current >= VAD_NO_SPEECH_TIMEOUT_MS
        ) {
          vadAutoStopRef.current = null;
          vadNoSpeechCancelRef.current?.();
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, []);

  const _stopBargeIn = useCallback(() => {
    if (bargeRafRef.current !== null) {
      cancelAnimationFrame(bargeRafRef.current);
      bargeRafRef.current = null;
    }
    try {
      bargeAnalyserRef.current?.disconnect();
    } catch {}
    bargeAnalyserRef.current = null;
    bargeBufferRef.current = null;
    bargeStreamRef.current?.getTracks().forEach((t) => t.stop());
    bargeStreamRef.current = null;
    bargeTriggerCountRef.current = 0;
  }, []);

  /**
   * Open a tiny watcher mic stream just for detecting the user talking
   * over Pilot. Only runs while TTS is playing; cleaned up immediately
   * on TTS end (or successful barge-in trigger).
   */
  const _startBargeIn = useCallback(async () => {
    if (!bargeInEnabledRef.current) return;
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: _MIC_CONSTRAINTS,
      });
      bargeStreamRef.current = stream;
      const ctx = getAudioContext(audioCtxRef);
      if (!ctx) return;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.4;
      source.connect(analyser);
      bargeAnalyserRef.current = analyser;
      bargeBufferRef.current = new Uint8Array(
        new ArrayBuffer(analyser.frequencyBinCount),
      );
      // Speaker→mic bleed is loudest at the very start of TTS; skip
      // the first BARGE_IN_WARMUP_MS so it can't false-fire on
      // Pilot's own opening syllable.
      const warmupUntil = performance.now() + BARGE_IN_WARMUP_MS;
      const tick = () => {
        const a = bargeAnalyserRef.current;
        const buf = bargeBufferRef.current;
        if (!a || !buf) return;
        if (performance.now() < warmupUntil) {
          bargeRafRef.current = requestAnimationFrame(tick);
          return;
        }
        a.getByteFrequencyData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
        const rms = Math.sqrt(sum / buf.length) / 255;
        if (rms > BARGE_IN_THRESHOLD) {
          bargeTriggerCountRef.current += 1;
          if (bargeTriggerCountRef.current >= BARGE_IN_FRAMES) {
            // User is talking over Pilot — cancel TTS, start fresh.
            _stopBargeIn();
            cancelTtsRef.current();
            void startRecordingRef.current();
            return;
          }
        } else {
          bargeTriggerCountRef.current = 0;
        }
        bargeRafRef.current = requestAnimationFrame(tick);
      };
      bargeRafRef.current = requestAnimationFrame(tick);
    } catch {
      // Permission denied or device gone — barge-in just becomes a
      // no-op for the rest of this turn. Not a hard failure.
    }
  }, [_stopBargeIn]);

  const _cleanupAudio = useCallback(() => {
    _stopAnalyser();
    _stopBargeIn();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    if (ttsElementSourceRef.current) {
      try {
        ttsElementSourceRef.current.disconnect();
      } catch {}
      ttsElementSourceRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, [_stopAnalyser, _stopBargeIn]);

  /**
   * Chain into a fresh recording after TTS finishes, if the user has
   * continuous mode on and we're still in a voice surface. Runs after
   * a small breath so the user has a moment to gather their thought.
   */
  const _suppressNextContinue = useCallback(() => {
    suppressContinueRef.current = true;
    if (suppressContinueTimerRef.current !== null) {
      window.clearTimeout(suppressContinueTimerRef.current);
    }
    // 200ms is enough for synth.cancel()'s onend to fire (it's
    // usually synchronous), but well below any natural utterance end
    // — so a future legitimate continue can't be eaten by mistake.
    suppressContinueTimerRef.current = window.setTimeout(() => {
      suppressContinueRef.current = false;
      suppressContinueTimerRef.current = null;
    }, 200);
  }, []);

  const _maybeContinueListening = useCallback(() => {
    _stopBargeIn();
    // Eat the flag if a programmatic cancel set it — explicit user
    // intent was "stop", not "stop then listen again".
    if (suppressContinueRef.current) {
      suppressContinueRef.current = false;
      if (suppressContinueTimerRef.current !== null) {
        window.clearTimeout(suppressContinueTimerRef.current);
        suppressContinueTimerRef.current = null;
      }
      return;
    }
    if (!continuousModeRef.current) return;
    window.setTimeout(() => {
      // Re-check in case the user closed voice mode during the breath.
      if (!continuousModeRef.current) return;
      void startRecordingRef.current();
    }, CONTINUOUS_RESUME_DELAY_MS);
  }, [_stopBargeIn]);

  const _speakWebSpeech = useCallback(
    (text: string): boolean => {
      if (
        typeof window === "undefined" ||
        !("speechSynthesis" in window) ||
        !text
      ) {
        return false;
      }
      const synth = window.speechSynthesis;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.05;
      u.pitch = 1;
      // Pick a friendly English voice if available.
      const voices = synth.getVoices();
      const pref =
        voices.find((v) => /Google.*US English/i.test(v.name)) ||
        voices.find((v) => /Samantha|Karen|Jenny|Aria/i.test(v.name)) ||
        voices.find((v) => v.lang?.startsWith("en"));
      if (pref) u.voice = pref;

      // Simulate amplitude from word boundaries — Web Speech doesn't
      // expose an audio node, so the orb pulses on each boundary event.
      u.onboundary = () => {
        smoothedRef.current = Math.min(1, smoothedRef.current * 0.4 + 0.55);
        setAmplitude(smoothedRef.current);
      };
      u.onend = () => {
        setStatus("idle");
        setAmplitude(0);
        _maybeContinueListening();
      };
      u.onerror = () => {
        setStatus("idle");
        setAmplitude(0);
        _stopBargeIn();
      };
      setStatus("speaking");
      synth.speak(u);
      // Fire-and-forget — barge-in is decoration.
      void _startBargeIn();
      return true;
    },
    [_maybeContinueListening, _startBargeIn, _stopBargeIn],
  );

  const _speak = useCallback(
    async (text: string, opts: { fast?: boolean } = {}) => {
      if (!voiceEnabled || !text) return;
      // Tearing down the previous TTS will synthesise an `onend` event
      // on the prior utterance. Suppress so it doesn't kick off a
      // continuous-listen we're about to override with new speech.
      _suppressNextContinue();
      _cleanupAudio();

      // TTS provider selection. ElevenLabs is the default so the user's
      // configured ELEVENLABS_VOICE_ID is actually heard. Web Speech is
      // only used when the user has explicitly opted into "Fast browser
      // voice" in the settings menu (sub-100ms latency, but ignores
      // ELEVENLABS_VOICE_ID — uses the browser's default voice).
      //
      // The opts.fast hint from a caller now means "the caller would
      // prefer fast if the user is OK with it" — the final decision is
      // the user's persisted preference.
      if (opts.fast && fastBrowserTtsRef.current && _speakWebSpeech(text)) {
        return;
      }

      setStatus("speaking");
      try {
        const blob = await api.pilot.tts(text);
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        const audio = new Audio(url);
        audio.crossOrigin = "anonymous";
        audioRef.current = audio;
        audio.onended = () => {
          setStatus("idle");
          _cleanupAudio();
          _maybeContinueListening();
        };
        audio.onerror = () => {
          setStatus("idle");
          _cleanupAudio();
        };
        const ctx = getAudioContext(audioCtxRef);
        if (ctx) {
          if (ctx.state === "suspended") {
            try {
              await ctx.resume();
            } catch {}
          }
          try {
            const elSource = ctx.createMediaElementSource(audio);
            ttsElementSourceRef.current = elSource;
            elSource.connect(ctx.destination);
            _startAnalyser(elSource);
          } catch {
            // Already connected — skip the analyser silently.
          }
        }
        await audio.play();
        // While ElevenLabs audio plays, watch the mic for the user
        // talking over it so we can cut Pilot off mid-sentence.
        void _startBargeIn();
      } catch (err) {
        if (err instanceof ApiError && _speakWebSpeech(text)) return;
        setStatus("idle");
      }
    },
    [
      voiceEnabled,
      _cleanupAudio,
      _startAnalyser,
      _speakWebSpeech,
      _maybeContinueListening,
      _startBargeIn,
      _suppressNextContinue,
    ],
  );

  const sendText = useCallback(
    async (text: string, opts: { stream?: boolean; fastTts?: boolean } = {}) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      setError(null);
      setInterimUserText(null);
      const userTurn = _appendTurn({ role: "user", content: trimmed });
      const pending = _appendTurn({
        role: "assistant",
        content: "",
        pending: true,
      });
      setStatus("thinking");

      const priorHistory: PilotTurn[] = history.map(({ role, content }) => ({
        role,
        content,
      }));

      try {
        if (opts.stream) {
          let accumulated = "";
          const res = await api.pilot.streamChat(
            trimmed,
            priorHistory,
            (evt: PilotStreamEvent) => {
              if (evt.type === "delta") {
                accumulated += evt.text;
                setHistory((h) =>
                  h.map((t) =>
                    t.id === pending.id
                      ? { ...t, content: accumulated, pending: false }
                      : t,
                  ),
                );
              } else if (evt.type === "trace") {
                setHistory((h) =>
                  h.map((t) =>
                    t.id === pending.id
                      ? { ...t, tool_trace: evt.trace }
                      : t,
                  ),
                );
                // Trace arrives BEFORE the text deltas — invalidate
                // here so list pages refresh *while* Pilot is still
                // narrating the result, not after the audio ends.
                _invalidateForTrace(queryClient, evt.trace);
              }
            },
          );
          // Final reply (full text) lands in the same turn for consistency.
          setHistory((h) =>
            h.map((t) =>
              t.id === pending.id
                ? {
                    ...t,
                    content: res.reply,
                    pending: false,
                    tool_trace: res.tool_trace,
                    outcome: res.outcome,
                  }
                : t,
            ),
          );
          await _speak(res.reply, { fast: opts.fastTts });
        } else {
          const res = await api.pilot.chat(trimmed, priorHistory);
          setHistory((h) =>
            h.map((t) =>
              t.id === pending.id
                ? {
                    ...t,
                    content: res.reply,
                    pending: false,
                    tool_trace: res.tool_trace,
                    outcome: res.outcome,
                  }
                : t,
            ),
          );
          _invalidateForTrace(queryClient, res.tool_trace);
          await _speak(res.reply, { fast: opts.fastTts });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
        setHistory((h) =>
          h.filter((t) => t.id !== pending.id && t.id !== userTurn.id),
        );
        setStatus("idle");
      }
    },
    [history, _appendTurn, _speak, queryClient],
  );

  /** Fetch a fresh greeting and speak it (used on voice-mode open). */
  const greet = useCallback(
    async (opts: { fastTts?: boolean } = {}) => {
      try {
        const { text } = await api.pilot.greeting();
        if (!text) return;
        _appendTurn({ role: "assistant", content: text });
        await _speak(text, { fast: opts.fastTts });
      } catch {
        // Pilot disabled / network error — stay silent rather than alarm.
      }
    },
    [_appendTurn, _speak],
  );

  /**
   * Speak a caller-supplied message and record it as an assistant turn.
   * Used for the post-login warm welcome where we want a deterministic
   * copy ("Welcome back, X…") instead of the dynamic /pilot/greeting.
   */
  const greetWithMessage = useCallback(
    async (text: string, opts: { fastTts?: boolean } = {}) => {
      if (!text) return;
      _appendTurn({ role: "assistant", content: text });
      await _speak(text, { fast: opts.fastTts });
    },
    [_appendTurn, _speak],
  );

  const startRecording = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Microphone not supported in this browser.");
      return;
    }
    const mime = pickMime();
    if (!mime) {
      setError("Audio recording not supported in this browser.");
      return;
    }
    try {
      _cleanupAudio();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: _MIC_CONSTRAINTS,
      });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        _stopAnalyser();
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: mime });
        chunksRef.current = [];
        if (blob.size === 0) {
          setStatus("idle");
          return;
        }
        setStatus("transcribing");
        try {
          const { text } = await api.pilot.stt(
            blob,
            `speech.${extFromMime(mime)}`,
          );
          if (text) {
            setInterimUserText(text);
            // Voice-mode invocations always come through startRecording —
            // use the fast streaming + Web Speech path for lower latency.
            await sendText(text, { stream: true, fastTts: true });
          } else {
            setStatus("idle");
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Transcription failed");
          setStatus("idle");
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setStatus("recording");

      // Prime VAD bookkeeping so the analyser tick can auto-stop us
      // once the user has spoken and then fallen silent.
      const startedAt = performance.now();
      vadStartedAtRef.current = startedAt;
      vadLastVoiceAtRef.current = startedAt;
      vadHasSpokenRef.current = false;
      vadAutoStopRef.current = () => {
        const r = recorderRef.current;
        if (r && r.state === "recording") r.stop();
        recorderRef.current = null;
      };
      // No-speech timeout: user opened the mic but never spoke.
      // Route through cancelTtsRef (== full cancel) so we don't send
      // empty audio AND don't let continuous-listen immediately re-arm
      // the mic into the same empty silence.
      vadNoSpeechCancelRef.current = () => {
        cancelTtsRef.current();
      };

      // Wire mic into the analyser so the orb ripples to the user's voice.
      const ctx = getAudioContext(audioCtxRef);
      if (ctx) {
        if (ctx.state === "suspended") {
          try {
            await ctx.resume();
          } catch {}
        }
        try {
          const micSource = ctx.createMediaStreamSource(stream);
          _startAnalyser(micSource);
        } catch {
          // Analyser is purely decorative; ignore failures.
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Microphone permission denied",
      );
      setStatus("idle");
    }
  }, [sendText, _cleanupAudio, _startAnalyser, _stopAnalyser]);

  const stopRecording = useCallback(() => {
    vadAutoStopRef.current = null;
    const r = recorderRef.current;
    if (r && r.state === "recording") r.stop();
    recorderRef.current = null;
  }, []);

  const cancel = useCallback(() => {
    vadAutoStopRef.current = null;
    // User asked to stop. Don't let the implicit onend fire continuous-
    // listen — they didn't ask for a fresh recording, they asked for
    // quiet.
    _suppressNextContinue();
    const r = recorderRef.current;
    if (r && r.state === "recording") r.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
    setInterimUserText(null);
    _cleanupAudio();
    setStatus("idle");
  }, [_cleanupAudio, _suppressNextContinue]);

  // Wire the late-bound refs that TTS-end callbacks + barge-in reach
  // for. We don't depend on the function identities; we depend on what
  // they currently DO at fire time — which is exactly what refs are for.
  useEffect(() => {
    startRecordingRef.current = startRecording;
  }, [startRecording]);
  useEffect(() => {
    cancelTtsRef.current = cancel;
  }, [cancel]);

  const clearHistory = useCallback(() => {
    setHistory([]);
    setError(null);
    cancel();
  }, [cancel]);

  useEffect(() => {
    return () => {
      cancel();
      if (suppressContinueTimerRef.current !== null) {
        window.clearTimeout(suppressContinueTimerRef.current);
        suppressContinueTimerRef.current = null;
      }
      if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
        try {
          audioCtxRef.current.close();
        } catch {}
        audioCtxRef.current = null;
      }
    };
  }, [cancel]);

  return {
    history,
    status,
    error,
    voiceEnabled,
    setVoiceEnabled,
    sendText,
    startRecording,
    stopRecording,
    cancel,
    clearHistory,
    speak: _speak,
    greet,
    greetWithMessage,
    // Phase 3 voice mode UI.
    amplitude,
    interimUserText,
    // Phase 4 conversation polish.
    continuousMode,
    setContinuousMode,
    bargeInEnabled,
    setBargeInEnabled,
    fastBrowserTts,
    setFastBrowserTts,
    wakeWordEnabled,
    setWakeWordEnabled,
  };
}

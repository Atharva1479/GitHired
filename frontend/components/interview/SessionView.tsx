"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Mic, MicOff, Volume2 } from "lucide-react";

import { useEndSession, useSubmitTurn } from "@/hooks/useInterview";
import InterviewOrb, { type OrbState } from "./InterviewOrb";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const LS_ORB_MODE = "githired_interview_orb_mode";

interface SessionState {
  session_id: number;
  questions: string[];
  total_questions: number;
}

function readOrbMode(): boolean {
  try {
    const v = localStorage.getItem(LS_ORB_MODE);
    return v === null ? true : v === "true";
  } catch {
    return true;
  }
}

export default function SessionView() {
  const router = useRouter();
  const { mutateAsync: submitTurn } = useSubmitTurn();
  const { mutateAsync: endSession } = useEndSession();

  const [session, setSession]           = useState<SessionState | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying]       = useState(false);
  const [isRecording, setIsRecording]   = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript]     = useState("");
  const [history, setHistory]           = useState<Array<{ question: string; answer: string }>>([]);
  const [ending, setEnding]             = useState(false);
  const [orbMode]                       = useState(readOrbMode);

  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const hasInitRef       = useRef(false);
  const audioRef         = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (hasInitRef.current) return;
    hasInitRef.current = true;
    const raw = localStorage.getItem("jp_interview_session");
    if (!raw) { router.replace("/interview"); return; }
    const s = JSON.parse(raw) as SessionState;
    setSession(s);
    void speakQuestion(s.questions[0]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function speakQuestion(question: string) {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(true);
    try {
      const res = await fetch(`${BASE}/pilot/tts`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question }),
      });
      if (!res.ok) { setIsPlaying(false); return; }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { setIsPlaying(false); URL.revokeObjectURL(url); audioRef.current = null; };
      await audio.play();
    } catch {
      setIsPlaying(false);
    }
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream);
    chunksRef.current = [];
    mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    mr.onstop = handleRecordingStop;
    mr.start();
    mediaRecorderRef.current = mr;
    setIsRecording(true);
    setTranscript("");
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    setIsRecording(false);
  }

  async function handleRecordingStop() {
    setIsTranscribing(true);
    try {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("audio", blob, "answer.webm");
      const res = await fetch(`${BASE}/pilot/stt`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      setTranscript((data.text as string) ?? "");
    } finally {
      setIsTranscribing(false);
    }
  }

  async function submitAnswer() {
    if (!session || !transcript.trim()) return;
    const q = session.questions[currentIndex];
    await submitTurn({
      sessionId: session.session_id,
      question_index: currentIndex,
      question: q,
      user_answer: transcript,
    });
    setHistory((prev) => [...prev, { question: q, answer: transcript }]);
    setTranscript("");

    if (currentIndex + 1 >= session.total_questions) {
      await handleEnd();
    } else {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      await speakQuestion(session.questions[next]);
    }
  }

  async function skipQuestion() {
    if (!session) return;
    const q = session.questions[currentIndex];
    await submitTurn({
      sessionId: session.session_id,
      question_index: currentIndex,
      question: q,
      user_answer: "[Skipped]",
    });
    setHistory((prev) => [...prev, { question: q, answer: "[Skipped]" }]);
    setTranscript("");
    if (currentIndex + 1 >= session.total_questions) {
      await confirmEnd();
    } else {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      await speakQuestion(session.questions[next]);
    }
  }

  function requestEnd() {
    setShowEndConfirm(true);
  }

  async function confirmEnd() {
    setShowEndConfirm(false);
    if (!session || ending) return;
    setEnding(true);
    await endSession(session.session_id);
    localStorage.removeItem("jp_interview_session");
    router.push(`/interview/report/${session.session_id}`);
  }

  async function handleEnd() {
    if (!session || ending) return;
    setEnding(true);
    await endSession(session.session_id);
    localStorage.removeItem("jp_interview_session");
    router.push(`/interview/report/${session.session_id}`);
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  const currentQuestion = session.questions[currentIndex];
  const progress        = (currentIndex / session.total_questions) * 100;
  const orbState: OrbState = isRecording ? "listening" : isPlaying ? "speaking" : "idle";
  const isLast = currentIndex + 1 >= session.total_questions;

  const endConfirmModal = showEndConfirm && (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="rounded-2xl border p-6 max-w-sm w-full mx-4 shadow-2xl"
        style={{ background: "#0d0d1a", borderColor: "#1a1a2e" }}
      >
        <h3 className="font-semibold text-base mb-1" style={{ color: "#f0f0f4" }}>End interview early?</h3>
        <p className="text-sm mb-5" style={{ color: "#70707a" }}>
          Your answers so far will be saved and a report will be generated.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={() => setShowEndConfirm(false)}
            className="px-4 py-2 rounded-xl border text-sm font-medium transition-colors"
            style={{ borderColor: "#2a2a40", color: "#a5b4fc" }}
          >
            Continue
          </button>
          <button
            onClick={confirmEnd}
            className="px-4 py-2 rounded-xl bg-red-500 text-white text-sm font-semibold hover:bg-red-600 transition-colors"
          >
            End Interview
          </button>
        </div>
      </div>
    </div>
  );

  /* ── ORB MODE ─────────────────────────────────────────────── */
  if (orbMode) {
    return (
      <div className="min-h-screen flex flex-col" style={{ background: "#060610" }}>
        {endConfirmModal}

        {/* Top bar */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid #1a1a2e" }}>
          <span className="text-sm font-semibold" style={{ color: "#a5b4fc" }}>AI Interview</span>
          <span className="text-sm" style={{ color: "#555" }}>
            {currentIndex + 1} / {session.total_questions}
          </span>
          <button
            onClick={requestEnd}
            disabled={ending}
            className="text-xs text-red-500 hover:underline disabled:opacity-50"
          >
            End
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-0.5" style={{ background: "#1a1a2e" }}>
          <div
            className="h-full bg-indigo-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Main */}
        <div className="flex-1 flex flex-col items-center justify-center gap-10 px-6 py-10">
          {/* Orb */}
          <InterviewOrb state={orbState} size={210} />

          {/* Status label */}
          <div className="text-center min-h-[20px]">
            {isPlaying && (
              <p className="text-sm animate-pulse" style={{ color: "#818cf8" }}>
                AI is speaking…
              </p>
            )}
            {isRecording && (
              <p className="text-sm animate-pulse" style={{ color: "#f87171" }}>
                Recording your answer…
              </p>
            )}
            {isTranscribing && (
              <p className="text-sm" style={{ color: "#555" }}>
                Transcribing…
              </p>
            )}
            {!isPlaying && !isRecording && !isTranscribing && transcript && (
              <p className="text-sm" style={{ color: "#6366f1" }}>Answer captured — submit when ready</p>
            )}
            {!isPlaying && !isRecording && !isTranscribing && !transcript && (
              <p className="text-sm" style={{ color: "#444" }}>Your turn — record your answer</p>
            )}
          </div>

          {/* Transcript preview */}
          {transcript && (
            <div
              className="w-full max-w-lg rounded-xl px-4 py-3 text-sm leading-relaxed"
              style={{ background: "#0d0d1a", border: "1px solid #1a1a2e", color: "#888" }}
            >
              {transcript}
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center gap-6">
            {/* Mic button — large circle */}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isPlaying || ending || isTranscribing}
              className="flex items-center justify-center rounded-full transition-all disabled:opacity-40"
              style={{
                width: 64,
                height: 64,
                background: isRecording ? "#ef4444" : "#18182a",
                border: `2px solid ${isRecording ? "#ef4444" : "#2a2a40"}`,
                boxShadow: isRecording ? "0 0 20px rgba(239,68,68,.4)" : "none",
              }}
            >
              {isRecording
                ? <MicOff className="w-6 h-6 text-white" />
                : <Mic className="w-6 h-6" style={{ color: "#818cf8" }} />
              }
            </button>

            {/* Submit */}
            <button
              onClick={submitAnswer}
              disabled={!transcript.trim() || ending || isTranscribing}
              className="px-6 py-3 rounded-xl font-semibold text-sm transition-colors disabled:opacity-40"
              style={{ background: "#4f46e5", color: "#fff" }}
            >
              {isLast ? "Finish Interview" : "Next →"}
            </button>

            {/* Skip */}
            <button
              onClick={skipQuestion}
              disabled={isRecording || ending || isTranscribing}
              className="text-xs disabled:opacity-30 transition-colors hover:underline"
              style={{ color: "#555" }}
            >
              Skip
            </button>
          </div>
        </div>

        {/* Previous answers footer */}
        {history.length > 0 && (
          <div
            className="px-6 py-3 max-w-xl mx-auto w-full"
            style={{ borderTop: "1px solid #1a1a2e" }}
          >
            <p className="text-xs mb-1.5" style={{ color: "#333" }}>Previous answers</p>
            <div className="space-y-1 max-h-20 overflow-y-auto">
              {history.map((h, i) => (
                <p key={i} className="text-xs" style={{ color: "#444" }}>
                  <span style={{ color: "#555", fontWeight: 600 }}>Q{i + 1}:</span>{" "}
                  {h.answer.length > 100 ? h.answer.slice(0, 100) + "…" : h.answer}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ── TEXT MODE (original) ─────────────────────────────────── */
  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {endConfirmModal}

      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <span className="text-sm font-semibold">AI Interview</span>
        <span className="text-sm text-[var(--color-text-2)]">
          Question {currentIndex + 1} / {session.total_questions}
        </span>
        <button
          onClick={requestEnd}
          disabled={ending}
          className="text-xs text-red-500 hover:underline disabled:opacity-50"
        >
          End Interview
        </button>
      </div>

      <div className="h-1 bg-[var(--color-border)]">
        <div className="h-full bg-indigo-500 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8 max-w-2xl mx-auto w-full py-10">
        <div className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <div className="flex items-start gap-3">
            <Volume2
              className={`w-5 h-5 mt-0.5 flex-shrink-0 transition-colors ${
                isPlaying ? "text-indigo-500 animate-pulse" : "text-[var(--color-text-3)]"
              }`}
            />
            <p className="text-base leading-relaxed">{currentQuestion}</p>
          </div>
        </div>

        {(transcript || isTranscribing) && (
          <div className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 text-sm text-[var(--color-text-2)] min-h-[60px]">
            {isTranscribing
              ? <span className="flex items-center gap-2 text-[var(--color-text-3)]"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Transcribing…</span>
              : transcript}
          </div>
        )}

        <div className="flex gap-4 items-center">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isPlaying || ending || isTranscribing}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 ${
              isRecording
                ? "bg-red-500 text-white animate-pulse"
                : "bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-indigo-400"
            }`}
          >
            {isRecording ? <><MicOff className="w-4 h-4" /> Stop Recording</> : <><Mic className="w-4 h-4" /> Record Answer</>}
          </button>
          <button
            onClick={submitAnswer}
            disabled={!transcript.trim() || ending || isTranscribing}
            className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {isLast ? "Finish Interview" : "Next Question →"}
          </button>
          <button
            onClick={skipQuestion}
            disabled={isRecording || ending || isTranscribing}
            className="text-xs text-[var(--color-text-3)] hover:underline disabled:opacity-40 transition-colors"
          >
            Skip
          </button>
        </div>

        {isPlaying && <p className="text-xs text-[var(--color-text-3)] animate-pulse">AI is speaking…</p>}
      </div>

      {history.length > 0 && (
        <div className="border-t border-[var(--color-border)] px-6 py-4 max-w-2xl mx-auto w-full">
          <p className="text-xs text-[var(--color-text-3)] mb-2 font-medium uppercase tracking-wide">Previous answers</p>
          <div className="space-y-1.5 max-h-28 overflow-y-auto">
            {history.map((h, i) => (
              <div key={i} className="text-xs text-[var(--color-text-2)]">
                <span className="font-medium text-[var(--color-text)]">Q{i + 1}:</span>{" "}
                {h.answer.length > 120 ? h.answer.slice(0, 120) + "…" : h.answer}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Mic, MicOff, Volume2 } from "lucide-react";

import { useEndSession, useSubmitTurn } from "@/hooks/useInterview";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface SessionState {
  session_id: number;
  questions: string[];
  total_questions: number;
}

export default function SessionView() {
  const router = useRouter();
  const { mutateAsync: submitTurn } = useSubmitTurn();
  const { mutateAsync: endSession } = useEndSession();

  const [session, setSession] = useState<SessionState | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [history, setHistory] = useState<Array<{ question: string; answer: string }>>([]);
  const [ending, setEnding] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const raw = localStorage.getItem("jp_interview_session");
    if (!raw) {
      router.replace("/interview");
      return;
    }
    const s = JSON.parse(raw) as SessionState;
    setSession(s);
    void speakQuestion(s.questions[0]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function speakQuestion(question: string) {
    setIsPlaying(true);
    try {
      const res = await fetch(`${BASE}/pilot/tts`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };
      await audio.play();
    } catch {
      setIsPlaying(false);
    }
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream);
    chunksRef.current = [];
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
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
  const progress = (currentIndex / session.total_questions) * 100;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
        <span className="text-sm font-semibold">AI Interview</span>
        <span className="text-sm text-[var(--color-text-2)]">
          Question {currentIndex + 1} / {session.total_questions}
        </span>
        <button
          onClick={handleEnd}
          disabled={ending}
          className="text-xs text-red-500 hover:underline disabled:opacity-50"
        >
          End Interview
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-[var(--color-border)]">
        <div
          className="h-full bg-indigo-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8 max-w-2xl mx-auto w-full py-10">
        {/* Question card */}
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

        {/* Transcript */}
        {(transcript || isTranscribing) && (
          <div className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 text-sm text-[var(--color-text-2)] min-h-[60px]">
            {isTranscribing ? (
              <span className="flex items-center gap-2 text-[var(--color-text-3)]">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Transcribing…
              </span>
            ) : (
              transcript
            )}
          </div>
        )}

        {/* Controls */}
        <div className="flex gap-4">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isPlaying || ending || isTranscribing}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 ${
              isRecording
                ? "bg-red-500 text-white animate-pulse"
                : "bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-indigo-400"
            }`}
          >
            {isRecording ? (
              <>
                <MicOff className="w-4 h-4" /> Stop Recording
              </>
            ) : (
              <>
                <Mic className="w-4 h-4" /> Record Answer
              </>
            )}
          </button>
          <button
            onClick={submitAnswer}
            disabled={!transcript.trim() || ending || isTranscribing}
            className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {currentIndex + 1 >= session.total_questions ? "Finish Interview" : "Next Question →"}
          </button>
        </div>

        {isPlaying && (
          <p className="text-xs text-[var(--color-text-3)] animate-pulse">AI is speaking…</p>
        )}
      </div>

      {/* Previous answers */}
      {history.length > 0 && (
        <div className="border-t border-[var(--color-border)] px-6 py-4 max-w-2xl mx-auto w-full">
          <p className="text-xs text-[var(--color-text-3)] mb-2 font-medium uppercase tracking-wide">
            Previous answers
          </p>
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

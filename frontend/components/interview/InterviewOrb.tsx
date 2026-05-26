"use client";

export type OrbState = "idle" | "speaking" | "listening";

interface InterviewOrbProps {
  state: OrbState;
  size?: number;
}

export default function InterviewOrb({ state, size = 200 }: InterviewOrbProps) {
  return (
    <div
      className="interview-blob-wrap"
      data-state={state}
      style={{ position: "relative", width: size, height: size }}
    >
      <div
        className="interview-blob"
        style={{ width: size, height: size }}
      />
      <div className="interview-blob-inner" />
    </div>
  );
}

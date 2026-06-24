import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { useReport } from "@/hooks/useInterview";
import type { InterviewReportResponse } from "@/lib/interview-api";

vi.mock("@/lib/interview-api", () => ({
  getReport: vi.fn(),
}));

import { getReport } from "@/lib/interview-api";

const PENDING_REPORT: InterviewReportResponse = { status: "pending" };

const READY_REPORT: InterviewReportResponse = {
  status: "ready",
  overall_score: 82,
  summary: "Good performance.",
  skill_breakdown: { communication: 85, technical: 79 },
  questions: [],
  session: {
    id: 42,
    topic: "System Design",
    role: "Senior Engineer",
    years_exp: "5",
    duration_min: 30,
    created_at: "2026-06-24T10:00:00Z",
  },
};

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useReport polling behaviour", () => {
  it("is disabled when sessionId is null", () => {
    const { result } = renderHook(() => useReport(null), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
    expect(getReport).not.toHaveBeenCalled();
  });

  it("polls every 3s while status is pending", async () => {
    vi.mocked(getReport).mockResolvedValue(PENDING_REPORT);
    const { result } = renderHook(() => useReport(42), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("pending");
  });

  it("stops polling when status transitions to ready", async () => {
    // First call returns pending, second returns ready
    vi.mocked(getReport)
      .mockResolvedValueOnce(PENDING_REPORT)
      .mockResolvedValue(READY_REPORT);

    const { result } = renderHook(() => useReport(42), { wrapper });
    await waitFor(() => expect(result.current.data?.status).toBe("ready"), {
      timeout: 10000,
    });
    expect(result.current.data?.overall_score).toBe(82);
  });

  it("exposes the report data fields when ready", async () => {
    vi.mocked(getReport).mockResolvedValue(READY_REPORT);
    const { result } = renderHook(() => useReport(42), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const data = result.current.data!;
    expect(data.status).toBe("ready");
    expect(data.overall_score).toBe(82);
    expect(data.session?.id).toBe(42);
  });
});

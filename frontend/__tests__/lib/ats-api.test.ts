import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { analyzeResume } from "@/lib/ats-api";

// Minimal valid AnalysisResult shape returned by a 200
const MOCK_RESULT = {
  overall_score: 75,
  grade: "B",
  sections: { found: [], missing: [], ats_risks: [] },
  keywords: { required_found: [], required_missing: [], preferred_found: [], preferred_missing: [] },
  suggestions: [],
};

function mockFetchOnce(status: number, body: unknown = {}) {
  const response = {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response;
  vi.mocked(global.fetch).mockResolvedValueOnce(response);
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("analyzeResume", () => {
  it("returns data immediately on 200", async () => {
    mockFetchOnce(200, MOCK_RESULT);
    const fd = new FormData();
    const promise = analyzeResume(fd);
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(result.overall_score).toBe(75);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("throws 'Gemini quota exceeded' on 429 without retrying", async () => {
    mockFetchOnce(429, { detail: "quota exceeded" });
    const fd = new FormData();
    const promise = analyzeResume(fd);
    // Attach rejection handler BEFORE running timers to avoid unhandled-rejection warning
    const assertion = expect(promise).rejects.toThrow("Gemini quota exceeded — try again in a moment.");
    await vi.runAllTimersAsync();
    await assertion;
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("throws immediately on 400 without retrying", async () => {
    mockFetchOnce(400, { detail: "Bad request" });
    const fd = new FormData();
    const promise = analyzeResume(fd);
    const assertion = expect(promise).rejects.toThrow("Bad request");
    await vi.runAllTimersAsync();
    await assertion;
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("throws immediately on 401 without retrying", async () => {
    mockFetchOnce(401, {});
    const fd = new FormData();
    const promise = analyzeResume(fd);
    const assertion = expect(promise).rejects.toThrow("Error 401");
    await vi.runAllTimersAsync();
    await assertion;
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("retries on 500 and succeeds on second attempt", async () => {
    mockFetchOnce(500, { detail: "Internal Server Error" });
    mockFetchOnce(200, MOCK_RESULT);
    const fd = new FormData();
    const promise = analyzeResume(fd);
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(result.overall_score).toBe(75);
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
  });

  it("retries up to 2 times then throws on persistent 500", async () => {
    mockFetchOnce(500, { detail: "Internal Server Error" });
    mockFetchOnce(500, { detail: "Internal Server Error" });
    mockFetchOnce(500, { detail: "Internal Server Error" });
    const fd = new FormData();
    const promise = analyzeResume(fd);
    const assertion = expect(promise).rejects.toThrow("Internal Server Error");
    await vi.runAllTimersAsync();
    await assertion;
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3);
  });

  it("surfaces the backend detail message on non-retryable error", async () => {
    mockFetchOnce(422, { detail: "Resume text too short" });
    const fd = new FormData();
    const promise = analyzeResume(fd);
    const assertion = expect(promise).rejects.toThrow("Resume text too short");
    await vi.runAllTimersAsync();
    await assertion;
  });

  it("falls back to 'Error <status>' when no detail field present", async () => {
    mockFetchOnce(503, {});
    mockFetchOnce(503, {});
    mockFetchOnce(503, {});
    const fd = new FormData();
    const promise = analyzeResume(fd);
    const assertion = expect(promise).rejects.toThrow("Error 503");
    await vi.runAllTimersAsync();
    await assertion;
  });
});

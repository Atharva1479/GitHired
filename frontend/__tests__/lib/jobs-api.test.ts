import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import type { JobResult } from "@/types/jobs";

// Mock fetch globally so no real HTTP requests go out
const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// Import after stubbing so the module uses our mock
import { searchJobs } from "@/lib/jobs-api";

function makeApiJob(overrides: Partial<JobResult> = {}): JobResult {
  return {
    id: 1,
    source: "jsearch",
    external_id: "ext-1",
    title: "Software Engineer",
    company: "Acme",
    location: "Remote",
    description: null,
    apply_url: "https://example.com/apply",
    posted_at: null,
    employment_type: "FULLTIME",
    skills: [],
    hours_old: 10,
    freshness_score: 0.8,
    freshness_label: "⚡",
    freshness_color: "green",
    est_applicants: "<10",
    velocity_label: null,
    bookmark_status: null,
    is_remote: false,
    salary_min: null,
    salary_max: null,
    salary_currency: null,
    tags: [],
    semantic_score: null,
    ...overrides,
  };
}

function mockFetchOk(data: unknown) {
  fetchMock.mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

describe("searchJobs — client-side employment_type filter", () => {
  beforeEach(() => fetchMock.mockReset());
  afterEach(() => vi.restoreAllMocks());

  it("returns all jobs when employment_type is not set", async () => {
    const jobs = [
      makeApiJob({ id: 1, employment_type: "FULLTIME" }),
      makeApiJob({ id: 2, employment_type: "PARTTIME" }),
      makeApiJob({ id: 3, employment_type: null }),
    ];
    mockFetchOk(jobs);
    const result = await searchJobs({ q: "engineer" });
    expect(result).toHaveLength(3);
  });

  it("filters by employment_type=full (case-insensitive substring match)", async () => {
    const jobs = [
      makeApiJob({ id: 1, employment_type: "FULLTIME" }),
      makeApiJob({ id: 2, employment_type: "PARTTIME" }),
      makeApiJob({ id: 3, employment_type: "CONTRACTOR" }),
    ];
    mockFetchOk(jobs);
    const result = await searchJobs({ q: "engineer", employment_type: "full" });
    expect(result.map((j) => j.id)).toEqual([1]);
  });

  it("keeps jobs with null employment_type when filtering", async () => {
    const jobs = [
      makeApiJob({ id: 1, employment_type: "FULLTIME" }),
      makeApiJob({ id: 2, employment_type: null }),
    ];
    mockFetchOk(jobs);
    const result = await searchJobs({ q: "engineer", employment_type: "full" });
    // null employment_type is kept (unknown = don't exclude)
    expect(result.map((j) => j.id)).toEqual([1, 2]);
  });

  it("sends q, location, remote_only, experience as query params", async () => {
    mockFetchOk([]);
    await searchJobs({
      q: "react engineer",
      location: "NYC",
      remote_only: true,
      experience: "senior",
    });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("q=react+engineer");
    expect(url).toContain("location=NYC");
    expect(url).toContain("remote_only=true");
    expect(url).toContain("experience=senior");
  });

  it("does NOT send employment_type to the backend", async () => {
    mockFetchOk([]);
    await searchJobs({ q: "engineer", employment_type: "full" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).not.toContain("employment_type");
  });

  it("throws on non-ok response", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Unauthorized" }),
    });
    await expect(searchJobs({ q: "engineer" })).rejects.toThrow("Unauthorized");
  });
});

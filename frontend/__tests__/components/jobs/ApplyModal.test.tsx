import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ApplyModal from "@/components/jobs/ApplyModal";
import type { JobResult } from "@/types/jobs";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockToastPush = vi.fn();
vi.mock("@/app/providers", () => ({
  useToast: () => ({ push: mockToastPush }),
}));

const mockMutateAsync = vi.fn();
const mockSimilarJobs = vi.fn();
// Wrap in a vi.fn() so individual tests can override isPending
const mockUseApplyAndTrack = vi.fn();

vi.mock("@/hooks/useJobs", () => ({
  useApplyAndTrack: () => mockUseApplyAndTrack(),
  useSimilarJobs: (id: number | null) => mockSimilarJobs(id),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("open", vi.fn());
  mockUseApplyAndTrack.mockReturnValue({ mutateAsync: mockMutateAsync, isPending: false });
  mockSimilarJobs.mockReturnValue({ data: undefined });
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeJob(overrides: Partial<JobResult> = {}): JobResult {
  return {
    id: 1,
    source: "jsearch",
    external_id: "ext-1",
    title: "Senior React Engineer",
    company: "Vercel",
    location: "Remote",
    description: "Build the future of the web",
    apply_url: "https://vercel.com/jobs/1",
    posted_at: null,
    employment_type: "FULLTIME",
    skills: [],
    hours_old: 2,
    freshness_score: 90,
    freshness_label: "🔥 <6h",
    freshness_color: "emerald",
    est_applicants: "<10",
    velocity_label: null,
    bookmark_status: null,
    is_remote: true,
    salary_min: null,
    salary_max: null,
    salary_currency: null,
    tags: [],
    semantic_score: null,
    ...overrides,
  };
}

// ── Confirm state tests ────────────────────────────────────────────────────────

describe("ApplyModal — confirm state", () => {
  it("shows job title and company", () => {
    render(
      <ApplyModal
        job={makeJob()}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByText("Senior React Engineer")).toBeInTheDocument();
    expect(screen.getByText("Vercel")).toBeInTheDocument();
  });

  it("shows Apply & Track button", () => {
    render(
      <ApplyModal
        job={makeJob()}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /apply & track/i })).toBeInTheDocument();
  });

  it("Cancel button calls onClose", async () => {
    const onClose = vi.fn();
    render(
      <ApplyModal job={makeJob()} onClose={onClose} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows 'Tracking…' label while request is in-flight", () => {
    mockUseApplyAndTrack.mockReturnValue({ mutateAsync: mockMutateAsync, isPending: true });
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /tracking/i })).toBeInTheDocument();
  });
});

// ── Apply flow ─────────────────────────────────────────────────────────────────

describe("ApplyModal — apply flow", () => {
  it("opens job URL in new tab when apply is clicked", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    expect(window.open).toHaveBeenCalledWith(
      "https://vercel.com/jobs/1",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("calls onSuccess with application_id on success", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    const onSuccess = vi.fn();
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={onSuccess} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(99));
  });

  it("transitions to success state and shows confirmation text", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() =>
      expect(screen.getByText("Added to tracker!")).toBeInTheDocument(),
    );
  });

  it("success state shows 'View in Tracker' link", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() =>
      expect(screen.getByRole("link", { name: /view in tracker/i })).toBeInTheDocument(),
    );
  });
});

// ── Error handling ─────────────────────────────────────────────────────────────

describe("ApplyModal — error handling", () => {
  it("shows 'already applied' toast and calls onClose on 409", async () => {
    mockMutateAsync.mockRejectedValue(
      new Error("already_applied:88"),
    );
    const onClose = vi.fn();
    render(
      <ApplyModal job={makeJob()} onClose={onClose} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() => {
      expect(mockToastPush).toHaveBeenCalledWith("error", "You've already applied to this job");
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("shows generic error toast on unexpected failure", async () => {
    mockMutateAsync.mockRejectedValue(new Error("Network error"));
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() =>
      expect(mockToastPush).toHaveBeenCalledWith(
        "error",
        "Failed to track application. Please try again.",
      ),
    );
  });

  it("does NOT call onSuccess on error", async () => {
    mockMutateAsync.mockRejectedValue(new Error("500 Server Error"));
    const onSuccess = vi.fn();
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={onSuccess} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() => expect(mockToastPush).toHaveBeenCalled());
    expect(onSuccess).not.toHaveBeenCalled();
  });
});

// ── Similar jobs ──────────────────────────────────────────────────────────────

describe("ApplyModal — similar jobs", () => {
  it("shows similar job titles in success state", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    mockSimilarJobs.mockReturnValue({
      data: [
        {
          id: 2,
          source: "adzuna",
          external_id: "s-2",
          title: "React Developer",
          company: "Netlify",
          freshness_label: "⚡ 6–24h",
          freshness_color: "green",
          apply_url: "https://netlify.com/jobs/2",
          location: null,
          description: null,
          posted_at: null,
          employment_type: null,
          skills: [],
          hours_old: 10,
          freshness_score: 70,
          est_applicants: "<20",
          velocity_label: null,
          bookmark_status: null,
          is_remote: false,
          salary_min: null,
          salary_max: null,
          salary_currency: null,
          tags: [],
          semantic_score: null,
        },
      ],
    });

    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() =>
      expect(screen.getByText("React Developer")).toBeInTheDocument(),
    );
  });

  it("hides similar jobs section when no similar jobs returned", async () => {
    mockMutateAsync.mockResolvedValue({ application_id: 99, bookmark_id: 1 });
    mockSimilarJobs.mockReturnValue({ data: [] });
    render(
      <ApplyModal job={makeJob()} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    await waitFor(() =>
      expect(screen.getByText("Added to tracker!")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Similar fresh roles")).not.toBeInTheDocument();
  });
});

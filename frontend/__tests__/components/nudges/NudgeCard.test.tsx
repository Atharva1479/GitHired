import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NudgeCard } from "@/components/nudges/NudgeCard";
import type { Nudge } from "@/lib/nudges";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockToastPush = vi.fn();
vi.mock("@/app/providers", () => ({
  useToast: () => ({ push: mockToastPush }),
}));

const mockMarkActedMutateAsync = vi.fn();
const mockSnoozeMutateAsync = vi.fn();
const mockUseMarkActed = vi.fn();
const mockUseSnooze = vi.fn();

vi.mock("@/hooks/useNudges", () => ({
  useMarkActed: () => mockUseMarkActed(),
  useSnooze:    () => mockUseSnooze(),
}));

vi.mock("@/components/drafts/DraftModal", () => ({
  DraftModal: () => null,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("date-fns", () => ({
  formatDistanceToNowStrict: vi.fn(() => "2 days ago"),
  parseISO: (s: string) => new Date(s),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUseMarkActed.mockReturnValue({ mutateAsync: mockMarkActedMutateAsync, isPending: false });
  mockUseSnooze.mockReturnValue({ mutateAsync: mockSnoozeMutateAsync });
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeNudge(overrides: Partial<Nudge> = {}): Nudge {
  return {
    id: 1,
    type: "application_followup",
    reference_type: "application",
    reference_id: 5,
    severity: "overdue",
    message: "**Stripe** needs a follow-up",
    fired_on_date: "2026-01-01",
    read_at: null,
    acted_at: null,
    snoozed_until: null,
    created_at: "2026-01-01T12:00:00Z",
    ...overrides,
  };
}

// ── Severity chips ────────────────────────────────────────────────────────────

describe("NudgeCard — severity chip", () => {
  it("shows 'Overdue' chip for severity=overdue", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "overdue" })} />);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("shows 'Due' chip for severity=due", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "due" })} />);
    expect(screen.getByText("Due")).toBeInTheDocument();
  });

  it("shows 'Heads up' chip for severity=info", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "info" })} />);
    expect(screen.getByText("Heads up")).toBeInTheDocument();
  });

  it("applies red chip classes for overdue severity", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "overdue" })} />);
    const chip = screen.getByText("Overdue");
    expect(chip.className).toContain("red");
  });

  it("applies amber chip classes for due severity", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "due" })} />);
    const chip = screen.getByText("Due");
    expect(chip.className).toContain("amber");
  });

  it("applies blue chip classes for info severity", () => {
    render(<NudgeCard nudge={makeNudge({ severity: "info" })} />);
    const chip = screen.getByText("Heads up");
    expect(chip.className).toContain("blue");
  });
});

// ── Message rendering ─────────────────────────────────────────────────────────

describe("NudgeCard — message", () => {
  it("renders the nudge message text", () => {
    render(<NudgeCard nudge={makeNudge({ message: "You should follow up" })} />);
    expect(screen.getByText("You should follow up")).toBeInTheDocument();
  });

  it("renders **bold** markdown as <strong>", () => {
    render(<NudgeCard nudge={makeNudge({ message: "**Stripe** needs attention" })} />);
    const bold = screen.getByText("Stripe").closest("strong");
    expect(bold).toBeInTheDocument();
  });

  it("renders type label", () => {
    render(<NudgeCard nudge={makeNudge({ type: "application_followup" })} />);
    expect(screen.getByText("Follow-up")).toBeInTheDocument();
  });
});

// ── Mark done ─────────────────────────────────────────────────────────────────

describe("NudgeCard — mark done", () => {
  it("renders Mark done button when dimmed=false (default)", () => {
    render(<NudgeCard nudge={makeNudge()} />);
    expect(screen.getByRole("button", { name: /mark done/i })).toBeInTheDocument();
  });

  it("hides Mark done button when dimmed=true", () => {
    render(<NudgeCard nudge={makeNudge()} dimmed />);
    expect(screen.queryByRole("button", { name: /mark done/i })).not.toBeInTheDocument();
  });

  it("calls useMarkActed.mutateAsync with nudge id on click", async () => {
    const user = userEvent.setup();
    mockMarkActedMutateAsync.mockResolvedValue(undefined);
    render(<NudgeCard nudge={makeNudge({ id: 7 })} />);
    await user.click(screen.getByRole("button", { name: /mark done/i }));
    expect(mockMarkActedMutateAsync).toHaveBeenCalledWith(7);
  });

  it("shows error toast when mark done fails", async () => {
    const user = userEvent.setup();
    mockMarkActedMutateAsync.mockRejectedValue(new Error("Server error"));
    render(<NudgeCard nudge={makeNudge()} />);
    await user.click(screen.getByRole("button", { name: /mark done/i }));
    await waitFor(() =>
      expect(mockToastPush).toHaveBeenCalledWith("error", "Server error"),
    );
  });
});

// ── Snooze ────────────────────────────────────────────────────────────────────

describe("NudgeCard — snooze", () => {
  it("snooze dropdown opens on button click", async () => {
    const user = userEvent.setup();
    render(<NudgeCard nudge={makeNudge()} />);
    await user.click(screen.getByRole("button", { name: /snooze/i }));
    expect(screen.getByText("3 days")).toBeInTheDocument();
  });

  it("calls useSnooze.mutateAsync with correct id and days", async () => {
    const user = userEvent.setup();
    mockSnoozeMutateAsync.mockResolvedValue(undefined);
    render(<NudgeCard nudge={makeNudge({ id: 3 })} />);
    await user.click(screen.getByRole("button", { name: /snooze/i }));
    await user.click(screen.getByText("3 days"));
    expect(mockSnoozeMutateAsync).toHaveBeenCalledWith({ id: 3, days: 3 });
  });

  it("shows success toast after snooze", async () => {
    const user = userEvent.setup();
    mockSnoozeMutateAsync.mockResolvedValue(undefined);
    render(<NudgeCard nudge={makeNudge()} />);
    await user.click(screen.getByRole("button", { name: /snooze/i }));
    await user.click(screen.getByText("1 day"));
    await waitFor(() =>
      expect(mockToastPush).toHaveBeenCalledWith("success", "Snoozed for 1d"),
    );
  });

  it("all three snooze options (1, 3, 7 days) visible after opening menu", async () => {
    const user = userEvent.setup();
    render(<NudgeCard nudge={makeNudge()} />);
    await user.click(screen.getByRole("button", { name: /snooze/i }));
    expect(screen.getByText("1 day")).toBeInTheDocument();
    expect(screen.getByText("3 days")).toBeInTheDocument();
    expect(screen.getByText("7 days")).toBeInTheDocument();
  });
});

// ── Draft button ──────────────────────────────────────────────────────────────

describe("NudgeCard — Draft button", () => {
  it("shows Draft button for application_followup type with reference_id", () => {
    render(<NudgeCard nudge={makeNudge({ type: "application_followup", reference_id: 5 })} />);
    expect(screen.getByRole("button", { name: /draft/i })).toBeInTheDocument();
  });

  it("shows Draft button for referral_ask type", () => {
    render(<NudgeCard nudge={makeNudge({ type: "referral_ask", reference_type: "referral", reference_id: 2 })} />);
    expect(screen.getByRole("button", { name: /draft/i })).toBeInTheDocument();
  });

  it("hides Draft button when reference_id is null", () => {
    render(<NudgeCard nudge={makeNudge({ type: "application_followup", reference_id: null })} />);
    expect(screen.queryByRole("button", { name: /draft/i })).not.toBeInTheDocument();
  });

  it("hides Draft button for non-draftable type (application_stale)", () => {
    render(<NudgeCard nudge={makeNudge({ type: "application_stale", reference_id: 5 })} />);
    expect(screen.queryByRole("button", { name: /draft/i })).not.toBeInTheDocument();
  });

  it("hides Draft button for apply_more type (no reference entity)", () => {
    render(<NudgeCard nudge={makeNudge({ type: "apply_more", reference_id: null })} />);
    expect(screen.queryByRole("button", { name: /draft/i })).not.toBeInTheDocument();
  });
});

// ── Dimmed state ──────────────────────────────────────────────────────────────

describe("NudgeCard — dimmed", () => {
  it("applies opacity class when dimmed=true", () => {
    const { container } = render(<NudgeCard nudge={makeNudge()} dimmed />);
    expect(container.firstChild).toHaveClass("opacity-55");
  });

  it("does NOT apply opacity class when dimmed=false", () => {
    const { container } = render(<NudgeCard nudge={makeNudge()} />);
    expect(container.firstChild).not.toHaveClass("opacity-55");
  });
});

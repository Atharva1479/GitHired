import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddApplication } from "@/components/applications/AddApplication";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockToastPush = vi.fn();
vi.mock("@/app/providers", () => ({
  useToast: () => ({ push: mockToastPush }),
}));

const mockCreateMutateAsync = vi.fn();
const mockUploadMutateAsync = vi.fn();
const mockUseCreate = vi.fn();
const mockUseUpload = vi.fn();

vi.mock("@/hooks/useApplications", () => ({
  useCreateApplication:      () => mockUseCreate(),
  useUploadApplicationFile:  () => mockUseUpload(),
}));

// Render Modal transparently so we can interact with form elements
vi.mock("@/components/ui/Modal", () => ({
  Modal: ({ open, children, title }: { open: boolean; children: React.ReactNode; title: string }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        {children}
      </div>
    ) : null,
}));

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockUseCreate.mockReturnValue({ mutateAsync: mockCreateMutateAsync, isPending: false });
  mockUseUpload.mockReturnValue({ mutateAsync: mockUploadMutateAsync, isPending: false });
});

// ── Helper ────────────────────────────────────────────────────────────────────

function renderForm(onClose = vi.fn()) {
  render(<AddApplication open onClose={onClose} />);
  return { onClose };
}

// ── Presence of required form fields ─────────────────────────────────────────

describe("AddApplication — form fields", () => {
  it("renders the Company input", () => {
    renderForm();
    expect(screen.getByLabelText(/company/i)).toBeInTheDocument();
  });

  it("renders the Role input", () => {
    renderForm();
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument();
  });

  it("renders the Source select", () => {
    renderForm();
    expect(screen.getByLabelText(/source/i)).toBeInTheDocument();
  });

  it("renders the Date applied input", () => {
    renderForm();
    expect(screen.getByLabelText(/date applied/i)).toBeInTheDocument();
  });

  it("renders the Job posting URL input", () => {
    renderForm();
    expect(screen.getByLabelText(/job posting url/i)).toBeInTheDocument();
  });

  it("renders the Job description textarea", () => {
    renderForm();
    expect(screen.getByLabelText(/job description/i)).toBeInTheDocument();
  });

  it("renders Resume and Cover letter PDF upload buttons", () => {
    renderForm();
    const uploadButtons = screen.getAllByRole("button", { name: /upload pdf/i });
    expect(uploadButtons).toHaveLength(2);
  });

  it("renders the Save application submit button", () => {
    renderForm();
    expect(screen.getByRole("button", { name: /save application/i })).toBeInTheDocument();
  });
});

// ── Busy state ────────────────────────────────────────────────────────────────

describe("AddApplication — loading state", () => {
  it("disables submit button and shows 'Saving…' when create is pending", () => {
    mockUseCreate.mockReturnValue({ mutateAsync: mockCreateMutateAsync, isPending: true });
    renderForm();
    const btn = screen.getByRole("button", { name: /saving/i });
    expect(btn).toBeDisabled();
  });

  it("disables submit button when upload is pending", () => {
    mockUseUpload.mockReturnValue({ mutateAsync: mockUploadMutateAsync, isPending: true });
    renderForm();
    const btn = screen.getByRole("button", { name: /saving/i });
    expect(btn).toBeDisabled();
  });
});

// ── Cancel ────────────────────────────────────────────────────────────────────

describe("AddApplication — cancel", () => {
  it("Cancel button calls onClose", async () => {
    const user = userEvent.setup();
    const { onClose } = renderForm();
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

// ── Submit flow ───────────────────────────────────────────────────────────────

describe("AddApplication — submit", () => {
  it("calls create.mutateAsync with company and role from inputs", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockResolvedValue({
      id: 99,
      company: "Stripe",
      role: "SWE",
    });

    renderForm();

    await user.clear(screen.getByLabelText(/company/i));
    await user.type(screen.getByLabelText(/company/i), "Stripe");
    await user.clear(screen.getByLabelText(/role/i));
    await user.type(screen.getByLabelText(/role/i), "SWE");

    await user.click(screen.getByRole("button", { name: /save application/i }));

    await waitFor(() =>
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ company: "Stripe", role: "SWE" }),
      ),
    );
  });

  it("shows success toast with company name on success", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockResolvedValue({ id: 1, company: "Vercel" });

    renderForm();

    await user.clear(screen.getByLabelText(/company/i));
    await user.type(screen.getByLabelText(/company/i), "Vercel");
    await user.clear(screen.getByLabelText(/role/i));
    await user.type(screen.getByLabelText(/role/i), "Engineer");

    await user.click(screen.getByRole("button", { name: /save application/i }));

    await waitFor(() =>
      expect(mockToastPush).toHaveBeenCalledWith("success", "Vercel added"),
    );
  });

  it("calls onClose after successful save", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockResolvedValue({ id: 1, company: "Vercel" });

    const { onClose } = renderForm();
    await user.clear(screen.getByLabelText(/company/i));
    await user.type(screen.getByLabelText(/company/i), "Vercel");
    await user.clear(screen.getByLabelText(/role/i));
    await user.type(screen.getByLabelText(/role/i), "Engineer");

    await user.click(screen.getByRole("button", { name: /save application/i }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("shows error toast when create.mutateAsync throws", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockRejectedValue(new Error("Network error"));

    renderForm();
    await user.clear(screen.getByLabelText(/company/i));
    await user.type(screen.getByLabelText(/company/i), "Acme");
    await user.clear(screen.getByLabelText(/role/i));
    await user.type(screen.getByLabelText(/role/i), "Dev");

    await user.click(screen.getByRole("button", { name: /save application/i }));

    await waitFor(() =>
      expect(mockToastPush).toHaveBeenCalledWith("error", "Network error"),
    );
  });

  it("does NOT call onClose on error", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockRejectedValue(new Error("Fail"));

    const { onClose } = renderForm();
    await user.clear(screen.getByLabelText(/company/i));
    await user.type(screen.getByLabelText(/company/i), "Acme");
    await user.clear(screen.getByLabelText(/role/i));
    await user.type(screen.getByLabelText(/role/i), "Dev");

    await user.click(screen.getByRole("button", { name: /save application/i }));
    await waitFor(() => expect(mockToastPush).toHaveBeenCalled());

    expect(onClose).not.toHaveBeenCalled();
  });

  it("includes source and applied_date in the create payload", async () => {
    const user = userEvent.setup();
    mockCreateMutateAsync.mockResolvedValue({ id: 1, company: "Y" });

    renderForm();
    await user.type(screen.getByLabelText(/company/i), "Y");
    await user.type(screen.getByLabelText(/role/i), "Dev");

    await user.click(screen.getByRole("button", { name: /save application/i }));

    await waitFor(() =>
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          source: expect.any(String),
          applied_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        }),
      ),
    );
  });
});

// ── File picker ───────────────────────────────────────────────────────────────

describe("AddApplication — FilePicker", () => {
  it("file inputs only accept PDF (accept attribute)", () => {
    renderForm();
    const fileInputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
    expect(fileInputs.length).toBeGreaterThanOrEqual(1);
    fileInputs.forEach((input) => {
      expect(input.accept).toBe("application/pdf");
    });
  });

  it("shows 'Upload PDF' label on both pickers when no file selected", () => {
    renderForm();
    const buttons = screen.getAllByRole("button", { name: /upload pdf/i });
    expect(buttons).toHaveLength(2);
  });
});

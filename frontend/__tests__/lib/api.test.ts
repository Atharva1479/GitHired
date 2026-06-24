import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, fileUrl } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const headerMap = new Map(Object.entries(headers));
  vi.mocked(global.fetch).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 204 ? "No Content" : "OK",
    headers: {
      get: (k: string) => headerMap.get(k) ?? null,
    },
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response);
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => {
  vi.unstubAllGlobals();
});

// ── ApiError ──────────────────────────────────────────────────────────────────

describe("ApiError", () => {
  it("is an instance of Error", () => {
    const err = new ApiError(404, "not_found", "Not found");
    expect(err).toBeInstanceOf(Error);
  });

  it("exposes status, type, message", () => {
    const err = new ApiError(422, "validation_error", "Invalid payload");
    expect(err.status).toBe(422);
    expect(err.type).toBe("validation_error");
    expect(err.message).toBe("Invalid payload");
  });

  it("name is 'Error' (not 'ApiError') — inherits from Error", () => {
    const err = new ApiError(500, "server_error", "Oops");
    expect(err.name).toBe("Error");
  });
});

// ── fileUrl ───────────────────────────────────────────────────────────────────

describe("fileUrl", () => {
  it("constructs a view URL without query string", () => {
    const url = fileUrl(42, "resume");
    expect(url).toContain("/applications/42/files/resume");
    expect(url).not.toContain("download");
  });

  it("appends ?download=1 when download=true", () => {
    const url = fileUrl(7, "cover_letter", true);
    expect(url).toContain("/applications/7/files/cover_letter");
    expect(url).toContain("download=1");
  });

  it("does not append download param when download=false", () => {
    const url = fileUrl(7, "jd", false);
    expect(url).not.toContain("download");
  });
});

// ── api.applications ──────────────────────────────────────────────────────────

describe("api.applications.list", () => {
  it("calls GET /applications and returns array", async () => {
    const apps = [{ id: 1, company: "Stripe" }];
    mockFetch(200, apps);
    const result = await api.applications.list();
    expect(result).toEqual(apps);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining("/applications"),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("appends ?status= when filter is provided", async () => {
    mockFetch(200, []);
    await api.applications.list({ status: "Interview" });
    const url = (vi.mocked(fetch).mock.calls[0][0] as string);
    expect(url).toContain("status=Interview");
  });

  it("throws ApiError with correct status on 401", async () => {
    mockFetch(401, { detail: "Not authenticated" });
    await expect(api.applications.list()).rejects.toMatchObject({
      status: 401,
      message: "Not authenticated",
    });
  });

  it("throws ApiError with body.title fallback when detail is absent", async () => {
    mockFetch(403, { title: "Forbidden" });
    await expect(api.applications.list()).rejects.toMatchObject({
      status: 403,
      message: "Forbidden",
    });
  });

  it("throws ApiError with statusText fallback when body is empty", async () => {
    mockFetch(500, {});
    await expect(api.applications.list()).rejects.toMatchObject({ status: 500 });
  });
});

describe("api.applications.create", () => {
  it("sends POST with JSON body", async () => {
    const payload = {
      company: "Vercel",
      role: "SWE",
      source: "LinkedIn" as const,
      applied_date: "2026-01-01",
    };
    mockFetch(200, { id: 99, ...payload });
    await api.applications.create(payload);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init as RequestInit).method).toBe("POST");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.company).toBe("Vercel");
  });
});

describe("api.applications.remove", () => {
  it("sends DELETE and returns null for 204 response", async () => {
    mockFetch(204, null);
    const result = await api.applications.remove(5);
    expect(result).toBeNull();
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init as RequestInit).method).toBe("DELETE");
  });
});

// ── Gamify header dispatch ─────────────────────────────────────────────────────

describe("X-Gamify header dispatch", () => {
  it("dispatches jp:gamify CustomEvent when header is present on a successful response", async () => {
    const envelope = {
      xp_gained: 10,
      new_level: null,
      streak: 3,
      quests_progressed: [],
      quest_completed: [],
      unlocked: [],
      duplicate: false,
    };
    mockFetch(200, [], { "X-Gamify": JSON.stringify(envelope) });

    const dispatched: CustomEvent[] = [];
    const handler = (e: Event) => dispatched.push(e as CustomEvent);
    window.addEventListener("jp:gamify", handler);

    await api.applications.list();

    window.removeEventListener("jp:gamify", handler);
    expect(dispatched).toHaveLength(1);
    expect(dispatched[0].detail).toMatchObject({ xp_gained: 10 });
  });

  it("does NOT dispatch when header is absent", async () => {
    mockFetch(200, []);
    const dispatched: Event[] = [];
    const handler = (e: Event) => dispatched.push(e);
    window.addEventListener("jp:gamify", handler);
    await api.applications.list();
    window.removeEventListener("jp:gamify", handler);
    expect(dispatched).toHaveLength(0);
  });
});

// ── api.nudges ────────────────────────────────────────────────────────────────

describe("api.nudges.snooze", () => {
  it("sends POST with days in body", async () => {
    mockFetch(204, null);
    await api.nudges.snooze(7, 3);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/nudges/7/snooze");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ days: 3 });
  });
});

describe("api.nudges.list", () => {
  it("appends unread=true query param", async () => {
    mockFetch(200, []);
    await api.nudges.list({ unread: true });
    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("unread=true");
  });

  it("appends severity param", async () => {
    mockFetch(200, []);
    await api.nudges.list({ severity: "overdue" });
    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    expect(url).toContain("severity=overdue");
  });
});

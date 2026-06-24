import { describe, expect, it } from "vitest";

import {
  companyAvatarClass,
  SOURCES,
  STATUSES,
  STATUS_META,
} from "@/lib/types";

describe("STATUSES", () => {
  it("contains all 6 valid kanban statuses", () => {
    expect(STATUSES).toEqual([
      "Applied",
      "Screening",
      "Interview",
      "Offer",
      "Rejected",
      "Ghosted",
    ]);
  });

  it("has no duplicates", () => {
    expect(new Set(STATUSES).size).toBe(STATUSES.length);
  });
});

describe("SOURCES", () => {
  it("contains the expected sources", () => {
    expect(SOURCES).toContain("LinkedIn");
    expect(SOURCES).toContain("Naukri");
    expect(SOURCES).toContain("Referral");
    expect(SOURCES).toContain("CompanySite");
    expect(SOURCES).toContain("Other");
  });
});

describe("STATUS_META", () => {
  it("has an entry for every status in STATUSES", () => {
    for (const s of STATUSES) {
      expect(STATUS_META).toHaveProperty(s);
    }
  });

  it("each entry has label, chip, dot, and columnAccent", () => {
    for (const s of STATUSES) {
      const meta = STATUS_META[s];
      expect(meta.label).toBeTruthy();
      expect(meta.chip).toBeTruthy();
      expect(meta.dot).toBeTruthy();
      expect(meta.columnAccent).toBeTruthy();
    }
  });

  it("label matches the status key for human-readable statuses", () => {
    expect(STATUS_META["Applied"].label).toBe("Applied");
    expect(STATUS_META["Offer"].label).toBe("Offer");
    expect(STATUS_META["Rejected"].label).toBe("Rejected");
  });

  it("chip classes include color-specific classes", () => {
    expect(STATUS_META["Applied"].chip).toContain("blue");
    expect(STATUS_META["Offer"].chip).toContain("emerald");
    expect(STATUS_META["Rejected"].chip).toContain("red");
    expect(STATUS_META["Ghosted"].chip).toContain("gray");
  });
});

describe("companyAvatarClass", () => {
  it("returns a non-empty string", () => {
    expect(companyAvatarClass("Google")).toBeTruthy();
  });

  it("is deterministic — same input always returns same class", () => {
    const cls1 = companyAvatarClass("Meta");
    const cls2 = companyAvatarClass("Meta");
    expect(cls1).toBe(cls2);
  });

  it("different company names can produce different classes", () => {
    const results = new Set(
      ["Google", "Apple", "Meta", "Amazon", "Netflix", "Stripe", "Vercel", "Figma", "Linear", "Notion"]
        .map(companyAvatarClass)
    );
    // At least 2 distinct classes across 10 companies
    expect(results.size).toBeGreaterThan(1);
  });

  it("returns a value containing Tailwind bg- and text- tokens", () => {
    const cls = companyAvatarClass("TestCo");
    expect(cls).toMatch(/bg-/);
    expect(cls).toMatch(/text-/);
  });

  it("handles empty string without throwing", () => {
    expect(() => companyAvatarClass("")).not.toThrow();
  });
});

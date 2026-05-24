"use client";

import { useState, type FormEvent } from "react";

import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useUpdateReferral } from "@/hooks/useReferrals";
import type { Referral, ReferralUpdate } from "@/lib/referrals";

function diff(before: Referral, next: ReferralUpdate): ReferralUpdate {
  const out: ReferralUpdate = {};
  for (const key of Object.keys(next) as (keyof ReferralUpdate)[]) {
    const a = (before as unknown as Record<string, unknown>)[key];
    const b = (next as unknown as Record<string, unknown>)[key];
    if ((a ?? null) !== (b ?? null)) {
      (out as Record<string, unknown>)[key] = b;
    }
  }
  return out;
}

export function EditReferralForm({
  referral,
  onDone,
  onCancel,
}: {
  referral: Referral;
  onDone: () => void;
  onCancel: () => void;
}) {
  const update = useUpdateReferral();
  const toast = useToast();

  const [name, setName] = useState(referral.name);
  const [company, setCompany] = useState(referral.company);
  const [targetRole, setTargetRole] = useState(referral.target_role);
  const [roleAtCompany, setRoleAtCompany] = useState(
    referral.role_at_company ?? "",
  );
  const [linkedinUrl, setLinkedinUrl] = useState(referral.linkedin_url ?? "");
  const [mutualContext, setMutualContext] = useState(
    referral.mutual_context ?? "",
  );
  const [notes, setNotes] = useState(referral.notes ?? "");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: ReferralUpdate = {
      name: name.trim(),
      company: company.trim(),
      target_role: targetRole.trim(),
      role_at_company: roleAtCompany.trim() || null,
      linkedin_url: linkedinUrl.trim() || null,
      mutual_context: mutualContext.trim() || null,
      notes: notes.trim() || null,
    };
    const patch = diff(referral, next);
    if (Object.keys(patch).length === 0) {
      onDone();
      return;
    }
    try {
      await update.mutateAsync({ id: referral.id, patch });
      toast.push("success", "Referral updated");
      onDone();
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Couldn't update",
      );
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <p className="text-[12px] text-[var(--color-text-3)]">
        Fields marked <span className="text-red-500">*</span> are required.
      </p>
      <Input
        id="er-name"
        label="Contact name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <div className="grid grid-cols-2 gap-3">
        <Input
          id="er-company"
          label="Company"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          required
        />
        <Input
          id="er-target"
          label="Target role"
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          required
        />
      </div>
      <Input
        id="er-role-at"
        label="Their role at the company"
        value={roleAtCompany}
        onChange={(e) => setRoleAtCompany(e.target.value)}
        placeholder="Senior Engineer"
      />
      <Input
        id="er-li"
        label="LinkedIn profile"
        type="url"
        value={linkedinUrl}
        onChange={(e) => setLinkedinUrl(e.target.value)}
        placeholder="https://linkedin.com/in/username"
      />
      <div className="space-y-1.5">
        <label
          htmlFor="er-mutual"
          className="block text-[13px] font-medium text-[var(--color-text)]"
        >
          Mutual context
        </label>
        <textarea
          id="er-mutual"
          value={mutualContext}
          onChange={(e) => setMutualContext(e.target.value)}
          rows={2}
          placeholder="How you know them — shared school, prior employer, mutual connection."
          className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
        />
      </div>
      <div className="space-y-1.5">
        <label
          htmlFor="er-notes"
          className="block text-[13px] font-medium text-[var(--color-text)]"
        >
          Notes
        </label>
        <textarea
          id="er-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Private notes — not sent to the contact."
          className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
        />
      </div>

      <div className="flex items-center justify-end gap-2 pt-4 border-t border-[var(--color-border)]">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}

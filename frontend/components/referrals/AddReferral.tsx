"use client";

import { useState, type FormEvent } from "react";

import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useCreateReferral } from "@/hooks/useReferrals";

export function AddReferral({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateReferral();
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);

  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [roleAtCompany, setRoleAtCompany] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [connectionSentDate, setConnectionSentDate] = useState(today);
  const [mutualContext, setMutualContext] = useState("");
  const [notes, setNotes] = useState("");

  function reset() {
    setName("");
    setCompany("");
    setTargetRole("");
    setRoleAtCompany("");
    setLinkedinUrl("");
    setConnectionSentDate(today);
    setMutualContext("");
    setNotes("");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await create.mutateAsync({
        name,
        company,
        target_role: targetRole,
        connection_sent_date: connectionSentDate,
        role_at_company: roleAtCompany || null,
        linkedin_url: linkedinUrl || null,
        mutual_context: mutualContext || null,
        notes: notes || null,
      });
      toast.push("success", `${name} added`);
      reset();
      onClose();
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Failed to add");
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New referral contact"
      subtitle="Log someone who can refer you internally. You can edit any field later."
    >
      <form onSubmit={submit} className="flex flex-col">
        <p className="text-[12px] text-[var(--color-text-3)] mb-3">
          Fields marked <span className="text-red-500">*</span> are required.
        </p>
        <div className="space-y-4">
          <Input
            id="r-name"
            label="Contact name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
            placeholder="Full name"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              id="r-company"
              label="Company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              required
              placeholder="Stripe"
            />
            <Input
              id="r-target"
              label="Target role"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              required
              placeholder="Software Engineer"
            />
          </div>
          <Input
            id="r-rolec"
            label="Their role at the company"
            value={roleAtCompany}
            onChange={(e) => setRoleAtCompany(e.target.value)}
            placeholder="Senior Engineer"
          />
          <Input
            id="r-li"
            label="LinkedIn profile"
            type="url"
            value={linkedinUrl}
            onChange={(e) => setLinkedinUrl(e.target.value)}
            placeholder="https://linkedin.com/in/username"
          />
          <Input
            id="r-date"
            label="Connection request date"
            type="date"
            value={connectionSentDate}
            onChange={(e) => setConnectionSentDate(e.target.value)}
            required
          />
          <div className="space-y-1.5">
            <label
              htmlFor="r-mutual"
              className="block text-[13px] font-medium text-[var(--color-text)]"
            >
              Mutual context
            </label>
            <textarea
              id="r-mutual"
              value={mutualContext}
              onChange={(e) => setMutualContext(e.target.value)}
              rows={2}
              placeholder="How you know them — shared school, prior employer, mutual connection."
              className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
            />
            <p className="text-[12px] text-[var(--color-text-3)]">
              Used to personalize your outreach message.
            </p>
          </div>
          <div className="space-y-1.5">
            <label
              htmlFor="r-notes"
              className="block text-[13px] font-medium text-[var(--color-text)]"
            >
              Notes
            </label>
            <textarea
              id="r-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Private notes — not sent to the contact."
              className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-4 mt-4 border-t border-[var(--color-border)]">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save referral"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

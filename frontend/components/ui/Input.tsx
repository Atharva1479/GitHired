"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
};

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { className, label, hint, id, required, ...props },
  ref,
) {
  return (
    <div className="space-y-1.5">
      {label ? (
        <label
          htmlFor={id}
          className="block text-[13px] font-medium text-[var(--color-text)]"
        >
          {label}
          {required ? (
            <span aria-hidden className="text-red-500 ml-0.5">
              *
            </span>
          ) : null}
        </label>
      ) : null}
      <input
        ref={ref}
        id={id}
        required={required}
        aria-required={required || undefined}
        className={cn(
          "w-full rounded-lg bg-[var(--color-surface)] px-3 h-10 text-[14px] text-[var(--color-text)]",
          "ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)]",
          "focus:outline-none focus:ring-2 focus:ring-indigo-500",
          "shadow-sm transition-shadow",
          className,
        )}
        {...props}
      />
      {hint ? <p className="text-[12px] text-[var(--color-text-3)]">{hint}</p> : null}
    </div>
  );
});

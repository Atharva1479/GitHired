"use client";

import { ChevronDown } from "lucide-react";
import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
};

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { className, label, id, children, required, ...props },
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
      <div className="relative">
        <select
          ref={ref}
          id={id}
          required={required}
          aria-required={required || undefined}
          className={cn(
            "w-full appearance-none rounded-lg bg-[var(--color-surface)] pl-3 pr-9 h-10 text-[14px] text-[var(--color-text)]",
            "ring-1 ring-inset ring-[var(--color-border)] shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500",
            className,
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          aria-hidden
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-3)]"
        />
      </div>
    </div>
  );
});

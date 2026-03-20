"use client";

import * as React from "react";

import { cn } from "@/core/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  invalid?: boolean;
};

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, invalid = false, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        "min-h-24 w-full rounded-md border border-neutral-300 bg-neutral-0 px-3 py-2 text-sm text-neutral-900 shadow-[inset_0_1px_1px_rgba(15,23,42,0.04)] outline-none transition-colors duration-150 ease-standard placeholder:text-neutral-400 focus-visible:ring-2 focus-visible:ring-primary/35",
        invalid ? "border-error focus-visible:ring-error/35" : "",
        className
      )}
      aria-invalid={invalid}
      data-ui="interactive"
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";


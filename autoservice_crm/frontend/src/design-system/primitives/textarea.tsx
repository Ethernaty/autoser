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
        "min-h-10 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 py-1 text-sm text-neutral-900 outline-none transition-colors duration-150 ease-standard placeholder:text-neutral-500 focus-visible:ring-2 focus-visible:ring-primary",
        invalid ? "border-error focus-visible:ring-error" : "",
        className
      )}
      aria-invalid={invalid}
      data-ui="interactive"
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";


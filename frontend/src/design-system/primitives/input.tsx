"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const inputVariants = cva(
  "w-full rounded-md border px-3 text-sm text-neutral-900 shadow-[inset_0_1px_1px_rgba(15,23,42,0.04)] outline-none transition-colors duration-150 ease-standard placeholder:text-neutral-400 focus-visible:ring-2 focus-visible:ring-primary/35 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-neutral-300 bg-neutral-0",
        subtle: "border-neutral-200 bg-neutral-50"
      },
      invalid: {
        true: "border-error focus-visible:ring-error/35",
        false: ""
      }
    },
    defaultVariants: {
      variant: "default",
      invalid: false
    }
  }
);

export type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> &
  VariantProps<typeof inputVariants> & {
    fullHeight?: "sm" | "md";
  };

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, invalid, fullHeight = "md", ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(inputVariants({ variant, invalid }), fullHeight === "md" ? "h-9" : "h-8", className)}
        data-ui="interactive"
        aria-invalid={invalid ?? false}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";


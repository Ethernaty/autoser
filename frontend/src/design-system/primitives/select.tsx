"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const selectVariants = cva(
  "w-full rounded-md border px-3 text-sm text-neutral-900 shadow-[inset_0_1px_1px_rgba(15,23,42,0.04)] outline-none transition-colors duration-150 ease-standard focus-visible:ring-2 focus-visible:ring-primary/35 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-neutral-300 bg-neutral-0",
        subtle: "border-neutral-200 bg-neutral-50"
      },
      invalid: {
        true: "border-error focus-visible:ring-error/35",
        false: ""
      },
      size: {
        sm: "h-8",
        md: "h-9"
      }
    },
    defaultVariants: {
      variant: "default",
      invalid: false,
      size: "md"
    }
  }
);

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> &
  VariantProps<typeof selectVariants>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant, invalid, size, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(selectVariants({ variant, invalid, size }), className)}
        data-ui="interactive"
        aria-invalid={invalid ?? false}
        {...props}
      />
    );
  }
);

Select.displayName = "Select";


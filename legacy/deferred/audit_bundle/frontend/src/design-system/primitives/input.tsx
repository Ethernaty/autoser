"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const inputVariants = cva(
  "w-full rounded-sm border px-2 text-sm text-neutral-900 outline-none transition-colors duration-150 ease-standard placeholder:text-neutral-500 focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "border-neutral-300 bg-neutral-0",
        subtle: "border-neutral-200 bg-neutral-50"
      },
      invalid: {
        true: "border-error focus-visible:ring-error",
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
        className={cn(inputVariants({ variant, invalid }), fullHeight === "md" ? "h-5" : "h-4", className)}
        data-ui="interactive"
        aria-invalid={invalid ?? false}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";


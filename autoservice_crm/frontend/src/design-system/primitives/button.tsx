"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1 rounded-sm border text-sm font-medium transition-colors duration-150 ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "border-primary bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80",
        secondary: "border-neutral-300 bg-neutral-0 text-neutral-900 hover:bg-neutral-50 active:bg-neutral-100",
        ghost: "border-transparent bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-200",
        destructive: "border-error bg-error text-neutral-0 hover:bg-error/90 active:bg-error/80",
        // Backward-compatible aliases.
        danger: "border-error bg-error text-neutral-0 hover:bg-error/90 active:bg-error/80",
        quiet: "border-neutral-200 bg-neutral-100 text-neutral-700 hover:bg-neutral-200 active:bg-neutral-200"
      },
      size: {
        sm: "h-4 min-w-4 px-2",
        md: "h-5 min-w-5 px-2.5",
        lg: "h-6 min-w-6 px-3"
      }
    },
    defaultVariants: {
      variant: "secondary",
      size: "md"
    }
  }
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    loading?: boolean;
  };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading = false, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        disabled={props.disabled || loading}
        data-ui="interactive"
        {...props}
      >
        {loading ? <span className="h-2 w-2 animate-spin rounded-full border-2 border-current border-r-transparent" /> : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";


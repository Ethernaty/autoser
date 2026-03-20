"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md border text-sm font-semibold leading-none transition-colors duration-150 ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "border-primary bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:bg-primary/85",
        secondary: "border-neutral-300 bg-neutral-0 text-neutral-900 hover:border-neutral-400 hover:bg-neutral-50 active:bg-neutral-100",
        ghost: "border-transparent bg-transparent text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 active:bg-neutral-200",
        destructive: "border-error bg-error text-neutral-0 shadow-sm hover:bg-error/90 active:bg-error/85",
        // Backward-compatible aliases.
        danger: "border-error bg-error text-neutral-0 shadow-sm hover:bg-error/90 active:bg-error/85",
        quiet: "border-neutral-200 bg-neutral-100 text-neutral-700 hover:border-neutral-300 hover:bg-neutral-200 active:bg-neutral-200"
      },
      size: {
        sm: "h-8 min-w-8 px-2.5 text-[13px]",
        md: "h-9 min-w-9 px-3",
        lg: "h-10 min-w-10 px-4"
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
        {loading ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent" /> : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";


import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium leading-4", {
  variants: {
    tone: {
      neutral: "border-neutral-200 bg-neutral-50 text-neutral-700",
      primary: "border-primary/20 bg-primary/10 text-primary",
      success: "border-success/25 bg-success/10 text-success",
      warning: "border-warning/25 bg-warning/10 text-warning",
      error: "border-error/25 bg-error/10 text-error",
      // Backward-compatible aliases.
      brand: "border-primary/20 bg-primary/10 text-primary",
      danger: "border-error/25 bg-error/10 text-error"
    }
  },
  defaultVariants: {
    tone: "neutral"
  }
});

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, tone, ...props }: BadgeProps): JSX.Element {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}


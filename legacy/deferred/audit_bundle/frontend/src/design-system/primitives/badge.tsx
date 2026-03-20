import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "bg-neutral-100 text-neutral-700",
      primary: "bg-primary/10 text-primary",
      success: "bg-success/10 text-success",
      warning: "bg-warning/10 text-warning",
      error: "bg-error/10 text-error",
      // Backward-compatible aliases.
      brand: "bg-primary/10 text-primary",
      danger: "bg-error/10 text-error"
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


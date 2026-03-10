import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const cardVariants = cva("rounded-md border", {
  variants: {
    type: {
      surface: "border-neutral-200 bg-neutral-0",
      bordered: "border-neutral-300 bg-neutral-0",
      elevated: "border-neutral-200 bg-neutral-0 shadow-sm",
      interactive: "border-neutral-200 bg-neutral-0 hover:border-neutral-300"
    }
  },
  defaultVariants: {
    type: "surface"
  }
});

type CardProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof cardVariants>;

export function Card({ className, type, ...props }: CardProps): JSX.Element {
  return <div className={cn(cardVariants({ type }), className)} data-ui={type === "interactive" ? "interactive" : undefined} {...props} />;
}


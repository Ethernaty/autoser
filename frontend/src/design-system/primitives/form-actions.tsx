import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type FormActionsProps = PropsWithChildren<{
  className?: string;
}>;

export function FormActions({ className, children }: FormActionsProps): JSX.Element {
  return <div className={cn("flex items-center justify-end gap-1 border-t border-neutral-200 pt-2", className)}>{children}</div>;
}


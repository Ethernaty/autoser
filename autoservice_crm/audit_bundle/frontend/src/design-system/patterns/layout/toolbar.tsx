import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type ToolbarProps = PropsWithChildren<{
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  className?: string;
}>;

export function Toolbar({ leading, trailing, className, children }: ToolbarProps): JSX.Element {
  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-2", className)}>
      <div className="min-w-0 flex-1">{leading ?? children}</div>
      {trailing ? <div className="flex flex-wrap items-center gap-1">{trailing}</div> : null}
    </div>
  );
}


import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type ToolbarProps = PropsWithChildren<{
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  className?: string;
}>;

export function Toolbar({ leading, trailing, className, children }: ToolbarProps): JSX.Element {
  return (
    <div className={cn("rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2", className)}>
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">{leading ?? children}</div>
        {trailing ? <div className="flex flex-wrap items-center gap-2">{trailing}</div> : null}
      </div>
    </div>
  );
}


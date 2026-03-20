import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";
import { Card } from "@/design-system/primitives/card";

type SectionProps = PropsWithChildren<{
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}>;

export function Section({ title, description, actions, className, children }: SectionProps): JSX.Element {
  return (
    <Card type="surface" className={cn("space-y-3 border-neutral-200 bg-neutral-0 p-4 shadow-sm", className)}>
      {title || description || actions ? (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-neutral-100 pb-3">
          <div>
            {title ? <h2 className="text-[18px] leading-6 font-semibold text-neutral-900">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm text-neutral-600">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </Card>
  );
}


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
    <Card type="surface" className={cn("space-y-2 border-neutral-200 p-3", className)}>
      {title || description || actions ? (
        <div className="flex flex-wrap items-start justify-between gap-2 border-b border-neutral-100 pb-2">
          <div>
            {title ? <h2 className="text-xl leading-[28px] font-semibold text-neutral-900">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm text-neutral-600">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-1">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </Card>
  );
}


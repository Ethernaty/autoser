import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type FormSectionProps = PropsWithChildren<{
  title?: string;
  description?: string;
  className?: string;
}>;

export function FormSection({ title, description, className, children }: FormSectionProps): JSX.Element {
  return (
    <section className={cn("space-y-2", className)}>
      {title || description ? (
        <div>
          {title ? <h3 className="text-base font-semibold text-neutral-900">{title}</h3> : null}
          {description ? <p className="mt-1 text-sm text-neutral-600">{description}</p> : null}
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">{children}</div>
    </section>
  );
}


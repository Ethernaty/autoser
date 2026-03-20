import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type FormFieldProps = PropsWithChildren<{
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  className?: string;
}>;

export function FormField({ id, label, required = false, hint, error, className, children }: FormFieldProps): JSX.Element {
  return (
    <div className={cn("space-y-1", className)}>
      <label className="text-sm font-medium text-neutral-700" htmlFor={id}>
        {label}
        {required ? <span className="ml-0.5 text-error">*</span> : null}
      </label>
      {children}
      {error ? <p className="text-xs text-error">{error}</p> : hint ? <p className="text-xs text-neutral-500">{hint}</p> : null}
    </div>
  );
}


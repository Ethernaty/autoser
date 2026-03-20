import { cn } from "@/core/lib/utils";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
};

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps): JSX.Element {
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-3 border-b border-neutral-200 pb-3", className)}>
      <div className="min-w-0">
        <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-neutral-900">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-3xl text-sm text-neutral-600">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}


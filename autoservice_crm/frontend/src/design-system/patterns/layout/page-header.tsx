import { cn } from "@/core/lib/utils";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
};

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps): JSX.Element {
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-2 border-b border-neutral-200 pb-2", className)}>
      <div className="min-w-0">
        <h1 className="text-[28px] leading-[36px] font-semibold text-neutral-900">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-neutral-600">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-1">{actions}</div> : null}
    </header>
  );
}


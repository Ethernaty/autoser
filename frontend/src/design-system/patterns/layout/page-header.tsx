import { cn } from "@/core/lib/utils";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
};

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps): JSX.Element {
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-2 border-b border-neutral-200 pb-2 sm:gap-3 sm:pb-2.5", className)}>
      <div className="min-w-0">
        <h1 className="text-[20px] leading-7 font-semibold tracking-tight text-neutral-900 sm:text-[22px]">{title}</h1>
        {subtitle ? <p className="mt-0.5 max-w-3xl text-xs leading-5 text-neutral-600 sm:text-[13px]">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}


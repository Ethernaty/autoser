import { type PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";
import { PageHeader } from "@/design-system/patterns/layout/page-header";

type PageLayoutProps = PropsWithChildren<{
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}>;

export function PageLayout({ title, subtitle, actions, className, children }: PageLayoutProps): JSX.Element {
  return (
    <section className={cn("space-y-3", className)}>
      <PageHeader title={title} subtitle={subtitle} actions={actions} />
      <div className="space-y-3">{children}</div>
    </section>
  );
}


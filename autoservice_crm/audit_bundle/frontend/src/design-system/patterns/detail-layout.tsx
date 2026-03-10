import { type PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type DetailLayoutProps = PropsWithChildren<{
  aside: React.ReactNode;
  className?: string;
}>;

export function DetailLayout({ aside, children, className }: DetailLayoutProps): JSX.Element {
  return (
    <div className={cn("grid grid-cols-12 gap-3", className)}>
      <div className="col-span-12 xl:col-span-8">{children}</div>
      <aside className="col-span-12 xl:col-span-4 xl:sticky xl:top-[72px] xl:self-start">{aside}</aside>
    </div>
  );
}


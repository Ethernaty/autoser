import type { CSSProperties, PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";
import { ContentContainer } from "@/design-system/patterns/layout/content-container";

type AppLayoutProps = PropsWithChildren<{
  sidebar: React.ReactNode;
  topbar: React.ReactNode;
  sidebarOffset: number;
  mobileNav?: React.ReactNode;
  modal?: React.ReactNode;
}>;

export function AppLayout({ sidebar, topbar, sidebarOffset, mobileNav, modal, children }: AppLayoutProps): JSX.Element {
  const layoutStyle = { "--sidebar-offset": `${sidebarOffset}px` } as CSSProperties;

  return (
    <div className="min-h-screen bg-neutral-100/70 text-neutral-900" style={layoutStyle}>
      {sidebar}
      <div className="min-h-screen pl-0 md:pl-[var(--sidebar-offset)]">
        {topbar}
        <main className={cn("pt-[56px]", mobileNav ? "pb-[72px] md:pb-0" : undefined)}>
          <ContentContainer>{children}</ContentContainer>
        </main>
      </div>
      {mobileNav}
      {modal}
    </div>
  );
}

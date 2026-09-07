import type { CSSProperties, PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";
import { ContentContainer } from "@/design-system/patterns/layout/content-container";

type AppLayoutProps = PropsWithChildren<{
  sidebar: React.ReactNode;
  topbar?: React.ReactNode;
  sidebarOffset: number;
  mobileNav?: React.ReactNode;
  modal?: React.ReactNode;
}>;

export function AppLayout({ sidebar, topbar, sidebarOffset, mobileNav, modal, children }: AppLayoutProps): JSX.Element {
  const layoutStyle = { "--sidebar-offset": `${sidebarOffset}px` } as CSSProperties;

  return (
    <div className="min-h-screen overflow-x-clip bg-neutral-50 text-neutral-900" style={layoutStyle}>
      {sidebar}
      <div className="min-h-screen min-w-0 pl-0 lg:pl-[var(--sidebar-offset)]">
        {topbar}
        <main
          className={cn(
            "min-h-screen",
            topbar ? "pt-[56px]" : "pt-0",
            mobileNav ? "pb-[calc(96px+env(safe-area-inset-bottom))] lg:pb-0" : undefined
          )}
        >
          <ContentContainer>{children}</ContentContainer>
        </main>
      </div>
      {mobileNav}
      {modal}
    </div>
  );
}

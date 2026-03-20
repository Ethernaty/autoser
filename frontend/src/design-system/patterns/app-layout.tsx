import type { PropsWithChildren } from "react";

import { ContentContainer } from "@/design-system/patterns/layout/content-container";

type AppLayoutProps = PropsWithChildren<{
  sidebar: React.ReactNode;
  topbar: React.ReactNode;
  sidebarOffset: number;
  modal?: React.ReactNode;
}>;

export function AppLayout({ sidebar, topbar, sidebarOffset, modal, children }: AppLayoutProps): JSX.Element {
  return (
    <div className="min-h-screen bg-neutral-100/70 text-neutral-900">
      {sidebar}
      <div className="min-h-screen" style={{ paddingLeft: sidebarOffset }}>
        {topbar}
        <main className="pt-[56px]">
          <ContentContainer>{children}</ContentContainer>
        </main>
      </div>
      {modal}
    </div>
  );
}


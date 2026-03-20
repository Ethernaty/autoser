"use client";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { AppLayout as AppLayoutPattern } from "@/design-system/patterns";
import { useUiStore } from "@/shared/ui/ui-store";
import { Header } from "@/widgets/app-shell/header";
import { ModalLayer } from "@/widgets/app-shell/modal-layer";
import { Sidebar } from "@/widgets/app-shell/sidebar";

export function AppLayout({ children, modal }: { children: React.ReactNode; modal: React.ReactNode }): JSX.Element {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);

  return (
    <AppLayoutPattern
      sidebar={<Sidebar collapsed={collapsed} />}
      topbar={<Header />}
      sidebarOffset={collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth}
      modal={<ModalLayer modal={modal} />}
    >
      {children}
    </AppLayoutPattern>
  );
}


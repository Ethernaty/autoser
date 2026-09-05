"use client";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { AppLayout as AppLayoutPattern } from "@/design-system/patterns";
import { useUiStore } from "@/shared/ui/ui-store";
import { MobileBottomNav } from "@/widgets/app-shell/mobile-bottom-nav";
import { ModalLayer } from "@/widgets/app-shell/modal-layer";
import { Sidebar } from "@/widgets/app-shell/sidebar";

export function AppLayout({ children, modal }: { children: React.ReactNode; modal: React.ReactNode }): JSX.Element {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);

  return (
    <AppLayoutPattern
      sidebar={<Sidebar collapsed={collapsed} />}
      sidebarOffset={collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth}
      mobileNav={<MobileBottomNav />}
      modal={<ModalLayer modal={modal} />}
    >
      {children}
    </AppLayoutPattern>
  );
}


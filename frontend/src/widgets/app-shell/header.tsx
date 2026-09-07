"use client";

import type { CSSProperties } from "react";
import { Bell, Command, PanelLeft } from "lucide-react";
import { usePathname } from "next/navigation";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { WorkspaceSwitcher } from "@/features/workspace/ui/workspace-switcher";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";
import { UserAccountMenu } from "@/widgets/app-shell/user-account-menu";

const sectionKeyByRoute: Array<{ route: string; key: string }> = [
  { route: ROUTES.dashboard, key: "shell.nav.dashboard" },
  { route: ROUTES.workOrders, key: "shell.nav.work_orders" },
  { route: ROUTES.clients, key: "shell.nav.clients" },
  { route: ROUTES.vehicles, key: "shell.nav.vehicles" },
  { route: ROUTES.employees, key: "shell.nav.employees" },
  { route: ROUTES.support, key: "shell.nav.support" },
  { route: ROUTES.settings, key: "shell.nav.settings" }
];

export function Header(): JSX.Element {
  const pathname = usePathname();
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen);
  const setMobileSidebarOpen = useUiStore((state) => state.setMobileSidebarOpen);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const { t } = useI18n();
  const sidebarOffset = collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth;
  const headerStyle = { "--sidebar-offset": `${sidebarOffset}px` } as CSSProperties;

  const currentSectionKey =
    sectionKeyByRoute.find((item) => pathname === item.route || pathname.startsWith(`${item.route}/`))?.key ?? "shell.nav.dashboard";

  return (
    <header
      className="fixed left-0 right-0 top-0 z-50 h-header border-b border-neutral-200/75 bg-neutral-0/90 backdrop-blur-sm md:left-[var(--sidebar-offset)]"
      style={headerStyle}
    >
      <div className="mx-auto flex h-full w-full max-w-content items-center gap-2 px-3 sm:px-4 lg:px-6">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-9 min-w-9 px-2 md:hidden"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label={t("shell.toggle_sidebar")}
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <div className="min-w-0">
          <p className="truncate text-[15px] font-semibold text-neutral-900">{t(currentSectionKey)}</p>
          <p className="hidden text-[11px] text-neutral-500 lg:block">{t("shell.brand")}</p>
        </div>

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <div className="hidden xl:block">
            <WorkspaceSwitcher compact hideError />
          </div>

          <button
            type="button"
            className="hidden h-8 items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-0 px-2.5 text-xs font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50 md:inline-flex"
            onClick={() => setCommandPaletteOpen(true)}
            title={t("shell.open_command_palette")}
            aria-label={t("shell.open_command_palette")}
          >
            <Command className="h-3.5 w-3.5 text-neutral-500" />
            <span>{t("shell.search_or_command")}</span>
            <span className="rounded border border-neutral-200 bg-neutral-50 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-500">
              Ctrl+K
            </span>
          </button>

          <Button type="button" variant="secondary" size="sm" className="h-8 min-w-8 rounded-lg border-neutral-200 px-2" aria-label={t("dashboard.activity.title")}>
            <Bell className="h-4 w-4 text-neutral-600" />
          </Button>

          <UserAccountMenu />
        </div>
      </div>
    </header>
  );
}

"use client";

import type { CSSProperties } from "react";
import { Command, PanelLeft } from "lucide-react";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { Button } from "@/design-system/primitives/button";
import { WorkspaceSwitcher } from "@/features/workspace/ui/workspace-switcher";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";
import { UserAccountMenu } from "@/widgets/app-shell/user-account-menu";

export function Header(): JSX.Element {
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen);
  const setMobileSidebarOpen = useUiStore((state) => state.setMobileSidebarOpen);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const { t } = useI18n();
  const sidebarOffset = collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth;
  const headerStyle = { "--sidebar-offset": `${sidebarOffset}px` } as CSSProperties;

  return (
    <header
      className="fixed left-0 right-0 top-0 z-50 h-header border-b border-neutral-200 bg-neutral-0 md:left-[var(--sidebar-offset)]"
      style={headerStyle}
    >
      <div className="mx-auto flex h-full w-full max-w-content items-center gap-2 px-2.5 sm:px-4">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-[32px] min-w-[32px] px-2 md:hidden"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label={t("shell.toggle_sidebar")}
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <div className="hidden min-w-0 md:block">
          <p className="truncate text-xs font-medium text-neutral-500">{t("shell.brand")}</p>
        </div>

        <div className="ml-auto flex h-[32px] shrink-0 items-center gap-1.5">
          <WorkspaceSwitcher compact hideError />

          <button
            type="button"
            className="hidden h-[32px] items-center gap-2 rounded-md border border-transparent bg-neutral-100 px-[10px] text-xs text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neutral-300 md:flex"
            onClick={() => setCommandPaletteOpen(true)}
            title={t("shell.open_command_palette")}
            aria-label={t("shell.open_command_palette")}
          >
            <Command className="h-3.5 w-3.5 text-neutral-500" />
            <span className="hidden md:inline">{t("shell.search_or_command")}</span>
            <span className="hidden xl:inline rounded border border-neutral-300 bg-neutral-50 px-[8px] py-[2px] text-[10px] font-medium text-neutral-500">
              Ctrl+K
            </span>
          </button>

          <UserAccountMenu />
        </div>
      </div>
    </header>
  );
}

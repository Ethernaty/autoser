"use client";

import { Command } from "lucide-react";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { WorkspaceSwitcher } from "@/features/workspace/ui/workspace-switcher";
import { useUiStore } from "@/shared/ui/ui-store";
import { UserAccountMenu } from "@/widgets/app-shell/user-account-menu";

export function Header(): JSX.Element {
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);

  return (
    <header
      className="fixed right-0 top-0 z-10 h-header border-b border-neutral-200 bg-neutral-0"
      style={{ left: collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth }}
    >
      <div className="mx-auto grid h-full w-full max-w-content grid-cols-[1fr_auto] items-center gap-2 px-4">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-neutral-500">AutoService CRM</p>
        </div>

        <div className="flex h-[32px] shrink-0 items-center gap-1.5">
          <WorkspaceSwitcher compact hideError />

          <button
            type="button"
            className="flex h-[32px] items-center gap-2 rounded-md border border-transparent bg-neutral-100 px-[10px] text-xs text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neutral-300"
            onClick={() => setCommandPaletteOpen(true)}
            title="Open command palette"
            aria-label="Open command palette"
          >
            <Command className="h-3.5 w-3.5 text-neutral-500" />
            <span className="hidden md:inline">Search or command</span>
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

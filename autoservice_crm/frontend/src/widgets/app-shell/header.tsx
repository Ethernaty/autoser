"use client";

import { Command } from "lucide-react";

import { LAYOUT_DIMENSIONS } from "@/core/config/constants";
import { Button } from "@/design-system/primitives/button";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { LogoutAction } from "@/features/auth/ui/logout-action";
import { usePlanCapabilities } from "@/features/subscription/hooks/use-plan-capabilities";
import { WorkspaceSwitcher } from "@/features/workspace/ui/workspace-switcher";
import { useUiStore } from "@/shared/ui/ui-store";

export function Header(): JSX.Element {
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen);
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const session = useAuthStore((state) => state.session);
  const { capabilities } = usePlanCapabilities();

  return (
    <header
      className="fixed right-0 top-0 z-10 h-header border-b border-neutral-200 bg-neutral-0"
      style={{ left: collapsed ? LAYOUT_DIMENSIONS.sidebarCollapsedWidth : LAYOUT_DIMENSIONS.sidebarWidth }}
    >
      <div className="mx-auto flex h-full w-full max-w-content items-center justify-between gap-2 px-3">
        <div className="min-w-0 flex-1 pr-1">
          <p className="truncate text-sm font-medium text-neutral-900">{session?.tenant.name ?? "Operator workspace"}</p>
          <p className="truncate text-xs text-neutral-600">
            {session ? `${session.user.email} • ${session.role}` : "Session loading"}
            {capabilities ? ` • ${capabilities.plan.toUpperCase()}` : ""}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1 overflow-x-auto">
          <WorkspaceSwitcher />
          <Button variant="secondary" size="sm" onClick={() => setCommandPaletteOpen(true)} title="Command palette" aria-label="Command palette">
            <Command className="h-2.5 w-2.5" />
            <span className="hidden lg:inline">Command</span>
          </Button>
          <LogoutAction />
        </div>
      </div>
    </header>
  );
}

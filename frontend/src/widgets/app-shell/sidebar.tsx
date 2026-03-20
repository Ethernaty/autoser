"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PanelLeftClose,
  Settings,
  UserCog,
  UsersRound,
  Car,
  ClipboardList
} from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useUiStore } from "@/shared/ui/ui-store";

const navGroups = [
  {
    label: "Operations",
    items: [
      { label: "Dashboard", href: ROUTES.dashboard, icon: LayoutDashboard },
      { label: "Work orders", href: ROUTES.workOrders, icon: ClipboardList },
      { label: "Clients", href: ROUTES.clients, icon: UsersRound },
      { label: "Vehicles", href: ROUTES.vehicles, icon: Car }
    ]
  },
  {
    label: "Team",
    items: [{ label: "Employees", href: ROUTES.employees, icon: UserCog }]
  },
  {
    label: "System",
    items: [{ label: "Settings", href: ROUTES.settings, icon: Settings }]
  }
] as const;

export function Sidebar({ collapsed }: { collapsed: boolean }): JSX.Element {
  const pathname = usePathname();
  const setCollapsed = useUiStore((state) => state.setSidebarCollapsed);
  const session = useAuthStore((state) => state.session);

  return (
    <aside
      className={
        "fixed left-0 top-0 z-20 h-screen border-r border-neutral-200 bg-neutral-0 shadow-sm transition-all duration-150 ease-standard " +
        (collapsed ? "w-sidebar-collapsed" : "w-sidebar")
      }
    >
      <div className={cn("flex h-header items-center border-b border-neutral-200 px-3", collapsed ? "justify-center" : "justify-between")}>
        {!collapsed ? (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-neutral-900">AutoService CRM</p>
            <p className="truncate text-xs text-neutral-500">{session?.tenant.slug ?? "workspace"}</p>
          </div>
        ) : null}
        <Button variant="ghost" size="sm" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>
      <nav className="space-y-4 p-2" aria-label="Primary navigation">
        {navGroups.map((group) => (
          <div key={group.label} className="space-y-1">
            {!collapsed ? <p className="px-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{group.label}</p> : null}
            {group.items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative flex h-9 w-full items-center rounded-md border text-sm transition-colors",
                    collapsed ? "justify-center px-0" : "gap-2 px-2.5",
                    isActive
                      ? "border-primary/25 bg-primary/10 text-primary"
                      : "border-transparent text-neutral-700 hover:border-neutral-200 hover:bg-neutral-50 hover:text-neutral-900"
                  )}
                  data-ui="interactive"
                >
                  <span
                    aria-hidden
                    className={cn(
                      "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full transition-colors",
                      isActive ? "bg-primary" : "bg-transparent"
                    )}
                  />
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed ? <span className="truncate font-medium">{item.label}</span> : null}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

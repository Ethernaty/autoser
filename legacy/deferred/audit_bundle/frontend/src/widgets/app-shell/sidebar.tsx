"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarClock,
  CircleDollarSign,
  ClipboardList,
  LayoutDashboard,
  PanelLeftClose,
  PlusSquare,
  UsersRound
} from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { cn } from "@/core/lib/utils";
import { useUiStore } from "@/shared/ui/ui-store";

const navItems = [
  { label: "Dashboard", href: ROUTES.dashboard, icon: LayoutDashboard },
  { label: "Orders", href: ROUTES.orders, icon: ClipboardList },
  { label: "New order", href: ROUTES.newOrder, icon: PlusSquare },
  { label: "Today", href: ROUTES.today, icon: CalendarClock },
  { label: "Clients", href: ROUTES.clients, icon: UsersRound },
  { label: "Cash desk", href: ROUTES.cashDesk, icon: CircleDollarSign }
] as const;

export function Sidebar({ collapsed }: { collapsed: boolean }): JSX.Element {
  const pathname = usePathname();
  const setCollapsed = useUiStore((state) => state.setSidebarCollapsed);

  return (
    <aside
      className={
        "fixed left-0 top-0 z-20 h-screen border-r border-neutral-200 bg-neutral-0 transition-all duration-150 ease-standard " +
        (collapsed ? "w-sidebar-collapsed" : "w-sidebar")
      }
    >
      <div className="flex h-header items-center justify-between border-b border-neutral-200 px-2">
        {!collapsed ? <span className="text-sm font-semibold text-neutral-900">AutoService</span> : null}
        <Button variant="ghost" size="sm" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">
          <PanelLeftClose className="h-2.5 w-2.5" />
        </Button>
      </div>
      <nav className="space-y-1 p-1" aria-label="Primary navigation">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex h-5 w-full items-center gap-1 rounded-sm border px-1.5 text-sm",
                isActive
                  ? "border-primary/25 bg-primary/10 text-primary"
                  : "border-transparent text-neutral-700 hover:bg-neutral-100"
              )}
              data-ui="interactive"
            >
              <item.icon className="h-2.5 w-2.5" />
              {!collapsed ? <span>{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}


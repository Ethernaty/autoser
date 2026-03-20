"use client";

import { useEffect } from "react";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";

import { ROUTES } from "@/core/config/routes";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { SkeletonState } from "@/shared/ui/skeleton-state";

export function ProtectedLayoutGuard({ children }: { children: React.ReactNode }): JSX.Element | null {
  const status = useAuthStore((state) => state.status);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status !== "unauthenticated") {
      return;
    }

    const next = pathname && pathname !== ROUTES.login ? `?next=${encodeURIComponent(pathname)}` : "";
    router.replace(`${ROUTES.login}${next}` as Route);
  }, [pathname, router, status]);

  if (status === "loading") {
    return <SkeletonState variant="page" />;
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}

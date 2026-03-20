"use client";

import { type PropsWithChildren } from "react";

import { QueryProvider } from "@/core/providers/query-provider";
import { ZustandProvider } from "@/core/providers/zustand-provider";
import { AuthBootstrap } from "@/features/auth/ui/auth-bootstrap";
import { UpgradeModalFoundation } from "@/features/subscription/ui/upgrade-modal-foundation";

export function AppProvider({ children }: PropsWithChildren): JSX.Element {
  return (
    <QueryProvider>
      <ZustandProvider>
        <AuthBootstrap>
          {children}
          <UpgradeModalFoundation />
        </AuthBootstrap>
      </ZustandProvider>
    </QueryProvider>
  );
}

"use client";

import { type PropsWithChildren } from "react";

import { QueryProvider } from "@/core/providers/query-provider";
import { ZustandProvider } from "@/core/providers/zustand-provider";
import { AuthBootstrap } from "@/features/auth/ui/auth-bootstrap";

export function AppProvider({ children }: PropsWithChildren): JSX.Element {
  return (
    <QueryProvider>
      <ZustandProvider>
        <AuthBootstrap>{children}</AuthBootstrap>
      </ZustandProvider>
    </QueryProvider>
  );
}

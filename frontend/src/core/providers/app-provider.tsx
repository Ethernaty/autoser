"use client";

import { type PropsWithChildren } from "react";

import { QueryProvider } from "@/core/providers/query-provider";
import { ZustandProvider } from "@/core/providers/zustand-provider";
import { AuthBootstrap } from "@/features/auth/ui/auth-bootstrap";
import { I18nProvider } from "@/shared/i18n";
import { ThemeProvider } from "@/shared/theme/theme-provider";

export function AppProvider({ children }: PropsWithChildren): JSX.Element {
  return (
    <QueryProvider>
      <ZustandProvider>
        <I18nProvider>
          <ThemeProvider>
            <AuthBootstrap>{children}</AuthBootstrap>
          </ThemeProvider>
        </I18nProvider>
      </ZustandProvider>
    </QueryProvider>
  );
}

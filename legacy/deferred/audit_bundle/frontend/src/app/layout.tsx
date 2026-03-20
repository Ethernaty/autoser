import type { Metadata } from "next";

import { AppProvider } from "@/core/providers/app-provider";
import { env } from "@/core/config/env";
import "@/styles/tailwind.css";

export const metadata: Metadata = {
  title: env.NEXT_PUBLIC_APP_NAME,
  description: "Enterprise SaaS frontend shell"
};

export default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <html lang="en">
      <body className="bg-background text-foreground antialiased">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}

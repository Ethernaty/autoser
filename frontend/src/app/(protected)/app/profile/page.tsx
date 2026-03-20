"use client";

import Link from "next/link";
import type { Route } from "next";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives";
import { PageLayout, Section } from "@/design-system/patterns";
import { useAuthStore } from "@/features/auth/model/auth-store";

export default function ProfilePage(): JSX.Element {
  const session = useAuthStore((state) => state.session);

  return (
    <PageLayout title="Profile" subtitle="Your current account context">
      <Section title="Account" description="Signed-in user details used in this workspace session.">
        <div className="space-y-2 text-sm">
          <div>
            <p className="text-xs text-neutral-500">Email</p>
            <p className="font-medium text-neutral-900">{session?.user.email ?? "Unknown"}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">Role</p>
            <p className="font-medium text-neutral-900">{session?.role ?? "Unknown"}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">Workspace</p>
            <p className="font-medium text-neutral-900">{session?.tenant.name ?? "Unknown"}</p>
          </div>
        </div>
        <div className="pt-2">
          <Link href={ROUTES.settings as Route}>
            <Button variant="secondary">Open settings</Button>
          </Link>
        </div>
      </Section>
    </PageLayout>
  );
}

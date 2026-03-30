"use client";

import Link from "next/link";
import type { Route } from "next";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives";
import { PageLayout, Section } from "@/design-system/patterns";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useI18n } from "@/shared/i18n";

export default function ProfilePage(): JSX.Element {
  const { t } = useI18n();
  const session = useAuthStore((state) => state.session);

  return (
    <PageLayout title={t("profile.title")} subtitle={t("profile.subtitle")}>
      <Section title={t("profile.account.title")} description={t("profile.account.description")}>
        <div className="space-y-2 text-sm">
          <div>
            <p className="text-xs text-neutral-500">{t("profile.email")}</p>
            <p className="font-medium text-neutral-900">{session?.user.email ?? t("common.unknown")}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">{t("profile.role")}</p>
            <p className="font-medium text-neutral-900">{session?.role ?? t("common.unknown")}</p>
          </div>
          <div>
            <p className="text-xs text-neutral-500">{t("profile.workspace")}</p>
            <p className="font-medium text-neutral-900">{session?.tenant.name ?? t("common.unknown")}</p>
          </div>
        </div>
        <div className="pt-2">
          <Link href={ROUTES.settings as Route}>
            <Button variant="secondary">{t("profile.open_settings")}</Button>
          </Link>
        </div>
      </Section>
    </PageLayout>
  );
}

"use client";

import { EmptyState } from "@/shared/ui/empty-state";
import { useI18n } from "@/shared/i18n";

export default function AppNotFound(): JSX.Element {
  const { t } = useI18n();
  return <EmptyState title={t("app.not_found.title")} description={t("app.not_found.description")} />;
}

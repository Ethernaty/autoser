"use client";

import Link from "next/link";
import type { Route } from "next";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { Button, FormField, Input } from "@/design-system/primitives";
import { PageLayout, Section } from "@/design-system/patterns";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { changePassword } from "@/features/auth/api/auth-api";
import { useI18n } from "@/shared/i18n";

export default function ProfilePage(): JSX.Element {
  const { t } = useI18n();
  const session = useAuthStore((state) => state.session);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const passwordMutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => { window.location.assign("/login"); }
  });

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
      <Section title={t("profile.password.title")} description={t("profile.password.description")}>
        <form className="max-w-xl space-y-3" onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          if (newPassword.length < 8) { setFormError(t("profile.password.too_short")); return; }
          if (newPassword !== confirmation) { setFormError(t("profile.password.mismatch")); return; }
          passwordMutation.mutate();
        }}>
          <FormField id="current-password" label={t("profile.password.current")} required>
            <Input id="current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
          </FormField>
          <FormField id="new-password" label={t("profile.password.new")} required>
            <Input id="new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </FormField>
          <FormField id="confirm-password" label={t("profile.password.confirm")} required>
            <Input id="confirm-password" type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </FormField>
          {formError ? <p className="text-sm text-error">{formError}</p> : null}
          {passwordMutation.error ? <p className="text-sm text-error">{passwordMutation.error.message}</p> : null}
          <Button type="submit" loading={passwordMutation.isPending}>{t("profile.password.submit")}</Button>
        </form>
      </Section>
    </PageLayout>
  );
}

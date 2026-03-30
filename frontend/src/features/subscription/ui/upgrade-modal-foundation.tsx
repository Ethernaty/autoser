"use client";

import { Button } from "@/design-system/primitives/button";
import { Modal } from "@/design-system/primitives/modal";
import { useUpgradeModalStore } from "@/features/subscription/model/upgrade-modal-store";
import { useI18n } from "@/shared/i18n";

function reasonLabel(reason: ReturnType<typeof useUpgradeModalStore.getState>["reason"], t: (key: string, params?: Record<string, string>) => string): string {
  if (!reason) {
    return t("upgrade.reason.default");
  }

  if (reason.kind === "feature") {
    return t("upgrade.reason.feature", { feature: reason.feature });
  }

  if (reason.kind === "limit") {
    return t("upgrade.reason.limit", { limit: reason.limitType });
  }

  return reason.message;
}

export function UpgradeModalFoundation(): JSX.Element {
  const { t } = useI18n();
  const open = useUpgradeModalStore((state) => state.open);
  const reason = useUpgradeModalStore((state) => state.reason);
  const close = useUpgradeModalStore((state) => state.close);

  return (
    <Modal
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          close();
        }
      }}
      title={t("upgrade.title")}
      description={reasonLabel(reason, t)}
      size="sm"
    >
      <div className="mt-2 flex justify-end gap-1">
        <Button variant="secondary" onClick={close}>
          {t("upgrade.close")}
        </Button>
        <Button disabled>{t("upgrade.soon")}</Button>
      </div>
    </Modal>
  );
}

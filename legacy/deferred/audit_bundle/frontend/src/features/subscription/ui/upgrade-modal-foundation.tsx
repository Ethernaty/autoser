"use client";

import { Button } from "@/design-system/primitives/button";
import { Modal } from "@/design-system/primitives/modal";
import { useUpgradeModalStore } from "@/features/subscription/model/upgrade-modal-store";

function reasonLabel(reason: ReturnType<typeof useUpgradeModalStore.getState>["reason"]): string {
  if (!reason) {
    return "Current workspace plan restricts this action.";
  }

  if (reason.kind === "feature") {
    return `Feature ${reason.feature} is available on a higher plan.`;
  }

  if (reason.kind === "limit") {
    return `Limit ${reason.limitType} has been reached for current billing period.`;
  }

  return reason.message;
}

export function UpgradeModalFoundation(): JSX.Element {
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
      title="Upgrade plan"
      description={reasonLabel(reason)}
      size="sm"
    >
      <div className="mt-2 flex justify-end gap-1">
        <Button variant="secondary" onClick={close}>
          Close
        </Button>
        <Button disabled>Upgrade (soon)</Button>
      </div>
    </Modal>
  );
}

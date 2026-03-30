"use client";

import { Button } from "@/design-system/primitives/button";
import { Modal } from "@/design-system/primitives/modal";
import { useI18n } from "@/shared/i18n";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive = false,
  loading = false,
  onConfirm
}: ConfirmDialogProps): JSX.Element {
  const { t } = useI18n();

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size="sm"
      footer={
        <div className="flex items-center justify-end gap-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {cancelLabel ?? t("common.cancel")}
          </Button>
          <Button variant={destructive ? "destructive" : "primary"} loading={loading} onClick={onConfirm}>
            {confirmLabel ?? t("confirm_dialog.confirm")}
          </Button>
        </div>
      }
    >
      <p className="text-sm text-neutral-700">{t("confirm_dialog.warning")}</p>
    </Modal>
  );
}

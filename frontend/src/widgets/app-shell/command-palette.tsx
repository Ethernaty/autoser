"use client";

import { Button } from "@/design-system/primitives/button";
import { Modal } from "@/design-system/primitives/modal";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";

export function CommandPalette(): JSX.Element {
  const { t } = useI18n();
  const open = useUiStore((state) => state.commandPaletteOpen);
  const setOpen = useUiStore((state) => state.setCommandPaletteOpen);

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title={t("command_palette.title")}
      description={t("command_palette.description")}
      size="md"
      footer={
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            {t("command_palette.close")}
          </Button>
        </div>
      }
    >
      <div className="space-y-1">
        <button className="flex h-5 w-full items-center rounded-md border border-neutral-200 px-2 text-left text-sm" type="button" data-ui="interactive">
          {t("command_palette.goto_workspace")}
        </button>
        <button className="flex h-5 w-full items-center rounded-md border border-neutral-200 px-2 text-left text-sm" type="button" data-ui="interactive">
          {t("command_palette.open_diagnostics")}
        </button>
      </div>
    </Modal>
  );
}

"use client";

import { Button } from "@/design-system/primitives/button";
import { Modal } from "@/design-system/primitives/modal";
import { useUiStore } from "@/shared/ui/ui-store";

export function CommandPalette(): JSX.Element {
  const open = useUiStore((state) => state.commandPaletteOpen);
  const setOpen = useUiStore((state) => state.setCommandPaletteOpen);

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title="Command palette"
      description="Global actions and navigation"
      size="md"
      footer={
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-1">
        <button className="flex h-5 w-full items-center rounded-md border border-neutral-200 px-2 text-left text-sm" type="button" data-ui="interactive">
          Go to workspace
        </button>
        <button className="flex h-5 w-full items-center rounded-md border border-neutral-200 px-2 text-left text-sm" type="button" data-ui="interactive">
          Open diagnostics
        </button>
      </div>
    </Modal>
  );
}

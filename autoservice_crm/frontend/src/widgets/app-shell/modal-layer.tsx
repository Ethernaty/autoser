"use client";

import { CommandPalette } from "@/widgets/app-shell/command-palette";

export function ModalLayer({ modal }: { modal: React.ReactNode }): JSX.Element {
  return (
    <>
      {modal}
      <CommandPalette />
    </>
  );
}

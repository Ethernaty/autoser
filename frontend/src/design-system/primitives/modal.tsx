"use client";

import * as Dialog from "@radix-ui/react-dialog";
import type { PropsWithChildren } from "react";

import { cn } from "@/core/lib/utils";

type ModalSize = "sm" | "md" | "lg";

const sizeClass: Record<ModalSize, string> = {
  sm: "max-w-[480px]",
  md: "max-w-[640px]",
  lg: "max-w-[800px]"
};

type ModalProps = PropsWithChildren<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  footer?: React.ReactNode;
  size?: ModalSize;
}>;

export function Modal({ open, onOpenChange, title, description, footer, size = "md", children }: ModalProps): JSX.Element {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-neutral-900/50" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 w-[calc(100%-32px)] -translate-x-1/2 -translate-y-1/2 rounded-md border border-neutral-200 bg-neutral-0 p-3 shadow-md",
            sizeClass[size]
          )}
        >
          {title ? <Dialog.Title className="text-xl leading-[28px] font-semibold text-neutral-900">{title}</Dialog.Title> : null}
          {description ? <Dialog.Description className="mt-1 text-sm text-neutral-600">{description}</Dialog.Description> : null}
          <div className="mt-3">{children}</div>
          {footer ? <div className="mt-3 border-t border-neutral-200 pt-2">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}


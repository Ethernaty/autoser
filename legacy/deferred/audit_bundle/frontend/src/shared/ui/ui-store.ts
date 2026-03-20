"use client";

import { create } from "zustand";

export type SkeletonVariant = "page" | "section" | "table";

type UiStore = {
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  globalLoading: boolean;
  globalError: string | null;
  setSidebarCollapsed: (value: boolean) => void;
  setCommandPaletteOpen: (value: boolean) => void;
  setGlobalLoading: (value: boolean) => void;
  setGlobalError: (value: string | null) => void;
};

export const useUiStore = create<UiStore>((set) => ({
  sidebarCollapsed: false,
  commandPaletteOpen: false,
  globalLoading: false,
  globalError: null,
  setSidebarCollapsed: (value) => set({ sidebarCollapsed: value }),
  setCommandPaletteOpen: (value) => set({ commandPaletteOpen: value }),
  setGlobalLoading: (value) => set({ globalLoading: value }),
  setGlobalError: (value) => set({ globalError: value })
}));

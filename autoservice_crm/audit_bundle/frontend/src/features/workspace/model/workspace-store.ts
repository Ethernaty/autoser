"use client";

import { create } from "zustand";

type WorkspaceState = {
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (workspaceId: string) => void;
  clearActiveWorkspace: () => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeWorkspaceId: null,
  setActiveWorkspaceId: (workspaceId) => set({ activeWorkspaceId: workspaceId }),
  clearActiveWorkspace: () => set({ activeWorkspaceId: null })
}));


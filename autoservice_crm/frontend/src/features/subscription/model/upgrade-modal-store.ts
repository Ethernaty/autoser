"use client";

import { create } from "zustand";

import type { PlanFeatureFlag, PlanLimitType } from "@/features/subscription/types/subscription-types";

type UpgradeReason =
  | { kind: "feature"; feature: PlanFeatureFlag }
  | { kind: "limit"; limitType: PlanLimitType }
  | { kind: "generic"; message: string };

type UpgradeModalState = {
  open: boolean;
  reason: UpgradeReason | null;
  openForFeature: (feature: PlanFeatureFlag) => void;
  openForLimit: (limitType: PlanLimitType) => void;
  openGeneric: (message: string) => void;
  close: () => void;
};

export const useUpgradeModalStore = create<UpgradeModalState>((set) => ({
  open: false,
  reason: null,
  openForFeature: (feature) => set({ open: true, reason: { kind: "feature", feature } }),
  openForLimit: (limitType) => set({ open: true, reason: { kind: "limit", limitType } }),
  openGeneric: (message) => set({ open: true, reason: { kind: "generic", message } }),
  close: () => set({ open: false, reason: null })
}));

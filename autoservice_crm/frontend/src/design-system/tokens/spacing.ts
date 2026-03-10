import { designTokens } from "@/design-system/tokens/design-tokens";

export const spacing = designTokens.spacing;

export const layoutSpacing = {
  pagePadding: designTokens.layout.pagePadding,
  sectionGap: designTokens.layout.sectionGap,
  toolbarGap: designTokens.layout.toolbarGap
} as const;

export type SpacingKey = keyof typeof spacing;


import { designTokens } from "@/design-system/tokens/design-tokens";

export const colors = {
  neutral: designTokens.color.neutral,
  primary: designTokens.color.primary,
  semantic: {
    success: designTokens.color.semantic.success,
    warning: designTokens.color.semantic.warning,
    error: designTokens.color.semantic.error
  },
  // Backward-compatible aliases for existing components.
  brand: designTokens.color.primary,
  danger: designTokens.color.semantic.error
} as const;


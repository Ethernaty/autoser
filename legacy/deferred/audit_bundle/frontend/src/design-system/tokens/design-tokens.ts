export const designTokens = {
  color: {
    primary: "#1D4ED8",
    neutral: {
      0: "#FFFFFF",
      50: "#F8FAFC",
      100: "#F1F5F9",
      200: "#E2E8F0",
      300: "#CBD5E1",
      400: "#94A3B8",
      500: "#64748B",
      600: "#475569",
      700: "#334155",
      800: "#1F2937",
      900: "#0F172A"
    },
    semantic: {
      success: "#15803D",
      warning: "#B45309",
      error: "#B91C1C"
    }
  },
  typography: {
    heading: {
      lg: { fontSize: 28, lineHeight: 36, fontWeight: 600 },
      md: { fontSize: 24, lineHeight: 32, fontWeight: 600 },
      sm: { fontSize: 20, lineHeight: 28, fontWeight: 600 }
    },
    body: {
      md: { fontSize: 16, lineHeight: 24, fontWeight: 400 },
      sm: { fontSize: 14, lineHeight: 20, fontWeight: 400 }
    },
    caption: { fontSize: 12, lineHeight: 16, fontWeight: 500 },
    weight: {
      regular: 400,
      medium: 500,
      semibold: 600
    }
  },
  spacing: {
    0: 0,
    8: 8,
    16: 16,
    24: 24,
    32: 32,
    40: 40,
    48: 48,
    56: 56,
    64: 64,
    72: 72,
    80: 80,
    96: 96,
    112: 112,
    128: 128
  },
  layout: {
    contentMaxWidth: 1280,
    sidebarWidth: 240,
    sidebarCollapsedWidth: 72,
    topbarHeight: 56,
    pagePadding: 24,
    sectionGap: 24,
    toolbarGap: 16
  },
  radius: {
    sm: 8,
    md: 12,
    lg: 16
  },
  shadow: {
    sm: "0 1px 2px rgba(15, 23, 42, 0.06)",
    md: "0 2px 8px rgba(15, 23, 42, 0.10)"
  }
} as const;

export type DesignTokens = typeof designTokens;


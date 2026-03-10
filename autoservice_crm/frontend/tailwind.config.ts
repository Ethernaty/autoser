import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/core/**/*.{ts,tsx}",
    "./src/design-system/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
    "./src/entities/**/*.{ts,tsx}",
    "./src/widgets/**/*.{ts,tsx}",
    "./src/shared/**/*.{ts,tsx}"
  ],
  theme: {
    container: {
      center: true,
      screens: {
        "2xl": "1280px"
      }
    },
    extend: {
      spacing: {
        1: "8px",
        2: "16px",
        3: "24px",
        4: "32px",
        5: "40px",
        6: "48px",
        7: "56px",
        8: "64px",
        9: "72px",
        10: "80px",
        12: "96px",
        14: "112px",
        16: "128px"
      },
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))"
        },
        neutral: {
          0: "hsl(var(--neutral-0))",
          50: "hsl(var(--neutral-50))",
          100: "hsl(var(--neutral-100))",
          200: "hsl(var(--neutral-200))",
          300: "hsl(var(--neutral-300))",
          400: "hsl(var(--neutral-400))",
          500: "hsl(var(--neutral-500))",
          600: "hsl(var(--neutral-600))",
          700: "hsl(var(--neutral-700))",
          800: "hsl(var(--neutral-800))",
          900: "hsl(var(--neutral-900))"
        },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        error: "hsl(var(--error))",
        // Backward-compatible aliases.
        brand: "hsl(var(--primary))",
        danger: "hsl(var(--error))"
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)"
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)"
      },
      height: {
        header: "56px"
      },
      width: {
        sidebar: "240px",
        "sidebar-collapsed": "72px"
      },
      maxWidth: {
        content: "1280px"
      },
      transitionTimingFunction: {
        standard: "cubic-bezier(0.2, 0, 0, 1)"
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
};

export default config;


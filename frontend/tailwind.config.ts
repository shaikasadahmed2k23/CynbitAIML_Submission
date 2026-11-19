import type { Config } from "tailwindcss";
import { theme } from "./src/theme";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: theme.colors,
      fontFamily: Object.fromEntries(Object.entries(theme.fonts).map(([k, v]) => [k, [...v]])),
      borderRadius: theme.radius,
      boxShadow: theme.shadow,
    },
  },
  plugins: [],
} satisfies Config;

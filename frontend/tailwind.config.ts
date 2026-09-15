import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        up: "#d1453b",
        down: "#22795e",
      },
    },
  },
  plugins: [],
} satisfies Config;

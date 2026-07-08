import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#f7f8fa",
        ink: "#172033",
        muted: "#667085",
        line: "#d9dee8",
        accent: "#2563eb",
      },
    },
  },
  plugins: [],
};

export default config;

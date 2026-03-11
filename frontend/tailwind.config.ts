import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        bg: "#ffffff",
        text: "#0f172a",
        muted: "#64748b",
        border: "#e2e8f0",
        bubbleUser: "#3b82f6",
        bubbleBot: "#f1f5f9",
        danger: "#ef4444",
      },
      borderRadius: {
        xl: "16px",
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;

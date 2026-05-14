/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./App.tsx",
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
    "./screens/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: "#6C63FF",
        surface: "#1A1A2E",
        background: "#0F0F1A",
        card: "#16213E",
        border: "#2A2A4A",
        text: "#E8E8F0",
        muted: "#8888AA",
        accent: "#00D4FF",
        danger: "#FF4444",
        success: "#00CC88",
      },
    },
  },
  plugins: [],
};
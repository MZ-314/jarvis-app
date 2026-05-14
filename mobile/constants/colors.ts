export const Colors = {
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

  voice: {
    idle: "#6C63FF",
    listening: "#00D4FF",
    thinking: "#FFB347",
    speaking: "#00CC88",
    error: "#FF4444",
  },
} as const;

export type ColorKey = keyof typeof Colors;
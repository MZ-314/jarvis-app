import { create } from "zustand";

type VoiceStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

interface VoiceState {
  status: VoiceStatus;
  transcript: string;
  response: string;
  isMuted: boolean;
  setStatus: (status: VoiceStatus) => void;
  setTranscript: (transcript: string) => void;
  setResponse: (response: string) => void;
  toggleMute: () => void;
  reset: () => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  status: "idle",
  transcript: "",
  response: "",
  isMuted: false,

  setStatus: (status) => set({ status }),
  setTranscript: (transcript) => set({ transcript }),
  setResponse: (response) => set({ response }),
  toggleMute: () => set((state) => ({ isMuted: !state.isMuted })),
  reset: () => set({ status: "idle", transcript: "", response: "" }),
}));
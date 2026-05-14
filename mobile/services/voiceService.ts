import { api } from "./api";

interface LiveKitTokenResponse {
  token: string;
  url: string;
  room: string;
}

interface TranscribeResponse {
  transcript: string;
}

interface SpeakResponse {
  audio_url: string;
}

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:5000") + "/api";

export const voiceService = {
  getLiveKitToken: async (conversationId: string) => {
    return api.post<LiveKitTokenResponse>("/voice/token", {
      conversation_id: conversationId,
    });
  },

  transcribe: async (audioBlob: Blob) => {
    const token = await import("../store/authStore").then(
      (m) => m.useAuthStore.getState().token
    );

    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");

    const response = await fetch(`${BASE_URL}/voice/transcribe`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Transcription failed");
    }

    return response.json() as Promise<TranscribeResponse>;
  },

  speak: async (text: string) => {
    return api.post<SpeakResponse>("/voice/speak", { text });
  },
};
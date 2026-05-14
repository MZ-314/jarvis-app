import { useRef, useCallback } from "react";
import { Audio } from "expo-av";
import { useVoiceStore } from "../store/voiceStore";
import { useChatStore } from "../store/chatStore";
import { useAuthStore } from "../store/authStore";
import { api } from "../services/api";

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:5000") + "/api";

interface AIResponse {
  response: string;
  conversation_id: string;
}

interface TranscribeResponse {
  transcript: string;
}

export function useVoice() {
  const { status, transcript, response, isMuted, setStatus, setTranscript, setResponse, reset } =
    useVoiceStore();
  const { addMessage, setConversationId, conversationId } = useChatStore();

  const recordingRef = useRef<Audio.Recording | null>(null);
  const sessionActive = useRef(false);
  const silenceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxDurationTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSpeechTime = useRef(0);
  const hasSpeech = useRef(false);

  const stopAndProcess = useCallback(async () => {
    if (!recordingRef.current) return;
    if (silenceTimer.current) {
      clearTimeout(silenceTimer.current);
      silenceTimer.current = null;
    }

    const recording = recordingRef.current;
    recordingRef.current = null;

    try {
      setStatus("thinking");
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();

      if (!uri || !hasSpeech.current) {
        if (sessionActive.current) {
          setStatus("listening");
          hasSpeech.current = false;
          startRecording();
        } else {
          setStatus("idle");
        }
        return;
      }

      const token = useAuthStore.getState().token;
      const formData = new FormData();
      formData.append("audio", { uri, type: "audio/wav", name: "recording.wav" } as any);

      const transcribeRes = await fetch(`${BASE_URL}/voice/transcribe`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const transcribeData: TranscribeResponse = await transcribeRes.json();
      const text = transcribeData.transcript?.trim();

      if (!text) {
        if (sessionActive.current) {
          setStatus("listening");
          hasSpeech.current = false;
          startRecording();
        } else {
          setStatus("idle");
        }
        return;
      }

      setTranscript(text);
      addMessage({
        id: Date.now().toString(),
        role: "user",
        content: text,
        timestamp: Date.now(),
      });

      const aiData = await api.post<AIResponse>("/ai/chat", {
        message: text,
        conversation_id: conversationId,
      });

      if (aiData.conversation_id) setConversationId(aiData.conversation_id);

      setResponse(aiData.response);
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: aiData.response,
        timestamp: Date.now(),
      });

      if (sessionActive.current) {
        setStatus("listening");
        hasSpeech.current = false;
        startRecording();
      } else {
        setStatus("idle");
      }
    } catch (e) {
      console.log("stopAndProcess error:", e);
      if (sessionActive.current) {
        setStatus("listening");
        hasSpeech.current = false;
        startRecording();
      } else {
        setStatus("error");
      }
    }
  }, [conversationId]);

  const startRecording = useCallback(async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        {
          android: {
            extension: ".wav",
            outputFormat: Audio.AndroidOutputFormat.DEFAULT,
            audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
            sampleRate: 16000,
            numberOfChannels: 1,
            bitRate: 128000,
            isMeteringEnabled: true,
          },
          ios: {
            extension: ".wav",
            audioQuality: Audio.IOSAudioQuality.HIGH,
            sampleRate: 16000,
            numberOfChannels: 1,
            bitRate: 128000,
            linearPCMBitDepth: 16,
            linearPCMIsBigEndian: false,
            linearPCMIsFloat: false,
            isMeteringEnabled: true,
          },
          web: {},
        },
        (status) => {
          if (!status.isRecording) return;
          const level = status.metering ?? -160;
          console.log("metering:", level);
          const isSpeaking = level > -45;

          if (isSpeaking) {
            hasSpeech.current = true;
            lastSpeechTime.current = Date.now();
            if (silenceTimer.current) {
              clearTimeout(silenceTimer.current);
              silenceTimer.current = null;
            }
          } else if (hasSpeech.current && !silenceTimer.current) {
            const silence = Date.now() - lastSpeechTime.current;
            if (silence > 800) {
              silenceTimer.current = setTimeout(() => {
                stopAndProcess();
              }, 300);
            }
          }
        },
        100
      );

      recordingRef.current = recording;
      hasSpeech.current = false;
      lastSpeechTime.current = 0;

      // Auto-submit after 15s as fallback
      if (maxDurationTimer.current) clearTimeout(maxDurationTimer.current);
      maxDurationTimer.current = setTimeout(() => {
        if (recordingRef.current) {
          hasSpeech.current = true;
          stopAndProcess();
        }
      }, 15000);
    } catch (e) {
      console.log("startRecording error:", e);
      setStatus("error");
    }
  }, [stopAndProcess]);

  const startSession = useCallback(async () => {
    if (sessionActive.current) return;

    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      setStatus("error");
      return;
    }

    sessionActive.current = true;
    reset();
    setStatus("listening");
    await startRecording();
  }, [startRecording]);

  const endSession = useCallback(async () => {
    sessionActive.current = false;
    if (silenceTimer.current) {
      clearTimeout(silenceTimer.current);
      silenceTimer.current = null;
    }
    if (maxDurationTimer.current) {
      clearTimeout(maxDurationTimer.current);
      maxDurationTimer.current = null;
    }
    if (recordingRef.current) {
      try {
        await recordingRef.current.stopAndUnloadAsync();
      } catch {}
      recordingRef.current = null;
    }
    reset();
  }, []);

  return {
    status,
    transcript,
    response,
    isMuted,
    startListening: startSession,
    stopListening: endSession,
    cancel: endSession,
    reset,
  };
}
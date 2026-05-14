import { View, Text, Pressable, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { VoiceOrb } from "../../components/VoiceOrb";
import { ChatBubble } from "../../components/ChatBubble";
import { useVoice } from "../../hooks/useVoice";
import { useChatStore } from "../../store/chatStore";
import { useAuth } from "../../hooks/useAuth";

const STATUS_LABELS: Record<string, string> = {
  idle: "Tap to start",
  listening: "Listening...",
  thinking: "Thinking...",
  speaking: "Speaking...",
  error: "Tap to try again",
};

export default function Voice() {
  const router = useRouter();
  const { status, startListening, stopListening, reset } = useVoice();
  const { messages } = useChatStore();
  const { logout, user } = useAuth();

  const handlePress = async () => {
    if (status === "error" || status === "idle") {
      reset();
      await startListening();
      return;
    }
    if (status === "listening" || status === "speaking" || status === "thinking") {
      await stopListening();
    }
  };

  const isActive = status !== "idle" && status !== "error";

  return (
    <SafeAreaView className="flex-1 bg-background">
      {/* Header */}
      <View className="flex-row items-center justify-between px-6 py-4 border-b border-border">
        <Text className="text-text text-lg font-semibold">
          Hey, {user?.name?.split(" ")[0] ?? "there"} 👋
        </Text>
        <View className="flex-row gap-4">
          <Pressable onPress={() => router.push("/(main)/chat")}>
            <Text className="text-muted text-sm">Chat</Text>
          </Pressable>
          <Pressable onPress={() => router.push("/(main)/memory")}>
            <Text className="text-muted text-sm">Memory</Text>
          </Pressable>
          <Pressable onPress={logout}>
            <Text className="text-danger text-sm">Logout</Text>
          </Pressable>
        </View>
      </View>

      {/* Chat history */}
      <ScrollView
        className="flex-1 px-4 py-4"
        contentContainerStyle={{ flexGrow: 1, justifyContent: "flex-end" }}
        showsVerticalScrollIndicator={false}
      >
        {messages.length === 0 ? (
          <View className="flex-1 items-center justify-center">
            <Text className="text-muted text-base text-center">
              Tap the orb to start talking.{"\n"}Jarvis is ready.
            </Text>
          </View>
        ) : (
          messages.map((msg) => <ChatBubble key={msg.id} message={msg} />)
        )}
      </ScrollView>

      {/* Voice Orb */}
      <View className="items-center pb-12 pt-8">
        <VoiceOrb
          status={status}
          onPressIn={handlePress}
          onPressOut={() => {}}
        />
        <Text className="text-muted text-sm mt-6">
          {STATUS_LABELS[status] ?? "Tap to start"}
        </Text>
        {isActive && (
          <Pressable onPress={stopListening} className="mt-4">
            <Text className="text-danger text-sm">End session</Text>
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}
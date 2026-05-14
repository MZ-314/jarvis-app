import { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Header } from "../../components/Header";
import { ChatBubble } from "../../components/ChatBubble";
import { useChatStore } from "../../store/chatStore";
import { api } from "../../services/api";

interface AIResponse {
  response: string;
  conversation_id: string;
}

export default function Chat() {
  const { messages, addMessage, setConversationId, conversationId, isLoading, setLoading } =
    useChatStore();
  const [input, setInput] = useState("");
  const scrollRef = useRef<ScrollView>(null);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    });

    setLoading(true);

    try {
      const data = await api.post<AIResponse>("/ai/chat", {
        message: text,
        conversation_id: conversationId,
      });

      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      addMessage({
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: Date.now(),
      });
    } catch (e: any) {
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-background">
      <Header title="Chat" showBack />

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        {/* Messages */}
        <ScrollView
          ref={scrollRef}
          className="flex-1 px-4 py-4"
          contentContainerStyle={{ flexGrow: 1, justifyContent: "flex-end" }}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() =>
            scrollRef.current?.scrollToEnd({ animated: true })
          }
        >
          {messages.length === 0 ? (
            <View className="flex-1 items-center justify-center">
              <Text className="text-muted text-base text-center">
                Start a conversation with Jarvis.
              </Text>
            </View>
          ) : (
            messages.map((msg) => <ChatBubble key={msg.id} message={msg} />)
          )}

          {isLoading && (
            <View className="self-start bg-card px-4 py-3 rounded-2xl rounded-tl-sm mb-3">
              <ActivityIndicator size="small" color="#6C63FF" />
            </View>
          )}
        </ScrollView>

        {/* Input */}
        <View className="flex-row items-end px-4 py-3 border-t border-border gap-3">
          <TextInput
            className="flex-1 bg-card border border-border rounded-2xl px-4 py-3 text-text text-base max-h-32"
            placeholder="Ask Jarvis anything..."
            placeholderTextColor="#8888AA"
            value={input}
            onChangeText={setInput}
            multiline
            onSubmitEditing={handleSend}
          />
          <Pressable
            className={`rounded-2xl px-4 py-3 ${input.trim() ? "bg-primary" : "bg-border"}`}
            onPress={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <Text className="text-white font-semibold">Send</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
import { View, Text } from "react-native";
import { Message } from "../store/chatStore";

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <View
      className={`mb-3 max-w-[80%] ${isUser ? "self-end" : "self-start"}`}
    >
      <View
        className={`px-4 py-3 rounded-2xl ${
          isUser
            ? "bg-primary rounded-tr-sm"
            : "bg-card rounded-tl-sm"
        }`}
      >
        <Text className="text-text text-base leading-6">{message.content}</Text>
      </View>
      <Text
        className={`text-muted text-xs mt-1 ${isUser ? "text-right" : "text-left"}`}
      >
        {new Date(message.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </Text>
    </View>
  );
}
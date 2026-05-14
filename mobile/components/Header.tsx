import { View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";

interface HeaderProps {
  title: string;
  showBack?: boolean;
  rightElement?: React.ReactNode;
}

export function Header({ title, showBack = false, rightElement }: HeaderProps) {
  const router = useRouter();

  return (
    <View className="flex-row items-center justify-between px-6 py-4 border-b border-border">
      <View className="w-10">
        {showBack && (
          <Pressable onPress={() => router.back()}>
            <Text className="text-primary text-2xl">‹</Text>
          </Pressable>
        )}
      </View>

      <Text className="text-text text-lg font-semibold tracking-wide">
        {title}
      </Text>

      <View className="w-10 items-end">
        {rightElement ?? null}
      </View>
    </View>
  );
}
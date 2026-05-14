import { useEffect } from "react";
import { View, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { useAuthStore } from "../store/authStore";

export default function Index() {
  const router = useRouter();
  const { token, isHydrated } = useAuthStore();

  useEffect(() => {
    if (!isHydrated) return;
    const timeout = setTimeout(() => {
      if (token) {
        router.replace("/(main)/voice");
      } else {
        router.replace("/(auth)/login");
      }
    }, 100);
    return () => clearTimeout(timeout);
  }, [isHydrated, token]);

  return (
    <View className="flex-1 items-center justify-center bg-background">
      <ActivityIndicator size="large" color="#6C63FF" />
    </View>
  );
}
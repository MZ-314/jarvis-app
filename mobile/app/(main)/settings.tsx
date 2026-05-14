import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Switch,
  Alert,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { useVoiceStore } from "../../store/voiceStore";
import { authService } from "../../services/authService";
import { router } from "expo-router";

export default function SettingsScreen() {
  const { user, clearAuth } = useAuthStore();
  const { isMuted, toggleMute } = useVoiceStore();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = () => {
    Alert.alert("Log Out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log Out",
        style: "destructive",
        onPress: async () => {
          setLoggingOut(true);
          try {
            await authService.logout();
          } catch (_) {}
          await clearAuth();
          router.replace("/(auth)/login");
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This will permanently delete your account and all data. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await authService.deleteAccount();
              await clearAuth();
              router.replace("/(auth)/login");
            } catch (_) {
              Alert.alert("Error", "Failed to delete account. Try again.");
            }
          },
        },
      ]
    );
  };

  const Section = ({
    title,
    children,
  }: {
    title: string;
    children: React.ReactNode;
  }) => (
    <View className="mb-6">
      <Text className="text-gray-400 text-xs font-semibold uppercase tracking-widest px-4 mb-2">
        {title}
      </Text>
      <View className="bg-gray-800 rounded-2xl mx-4 overflow-hidden">
        {children}
      </View>
    </View>
  );

  const Row = ({
    label,
    value,
    onPress,
    danger,
    right,
  }: {
    label: string;
    value?: string;
    onPress?: () => void;
    danger?: boolean;
    right?: React.ReactNode;
  }) => (
    <TouchableOpacity
      onPress={onPress}
      disabled={!onPress && !right}
      className="flex-row items-center justify-between px-4 py-4 border-b border-gray-700 last:border-b-0"
      activeOpacity={onPress ? 0.6 : 1}
    >
      <Text
        className={`text-base font-medium ${danger ? "text-red-400" : "text-white"}`}
      >
        {label}
      </Text>
      {right ?? (
        <Text className="text-gray-400 text-sm">{value ?? ""}</Text>
      )}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView className="flex-1 bg-gray-950">
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        <Text className="text-white text-2xl font-bold px-4 pt-2 pb-6">
          Settings
        </Text>

        <Section title="Account">
          <Row label="Name" value={user?.name ?? "—"} />
          <Row label="Email" value={user?.email ?? "—"} />
          <Row
            label="Change Password"
            value="›"
            onPress={() => router.push("/(main)/change-password" as never)}
          />
        </Section>

        <Section title="Voice">
          <Row
            label="Mute Microphone"
            right={
              <Switch
                value={isMuted}
                onValueChange={toggleMute}
                trackColor={{ false: "#374151", true: "#6366f1" }}
                thumbColor="#ffffff"
              />
            }
          />
        </Section>

        <Section title="Danger Zone">
          <Row label="Log Out" onPress={handleLogout} danger />
          <Row label="Delete Account" onPress={handleDeleteAccount} danger />
        </Section>

        {loggingOut && (
          <ActivityIndicator color="#6366f1" className="mt-4" />
        )}

        <Text className="text-gray-600 text-xs text-center mt-6">
          Jarvis v1.0.0
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
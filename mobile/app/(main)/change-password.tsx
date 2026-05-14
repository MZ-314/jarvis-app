import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { api } from "../../services/api";

export default function ChangePasswordScreen() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!current || !next || !confirm) {
      Alert.alert("Error", "All fields are required.");
      return;
    }
    if (next.length < 8) {
      Alert.alert("Error", "New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      Alert.alert("Error", "New passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      Alert.alert("Success", "Password changed.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch (err: any) {
      const msg =
        err?.message ?? "Failed to change password.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-gray-950">
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        className="flex-1"
      >
        <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled">
          <View className="flex-1 px-6 pt-4 pb-10">
            <TouchableOpacity onPress={() => router.back()} className="mb-6">
              <Text className="text-indigo-400 text-base">← Back</Text>
            </TouchableOpacity>

            <Text className="text-white text-2xl font-bold mb-8">
              Change Password
            </Text>

            <Text className="text-gray-400 text-xs mb-1 ml-1">Current Password</Text>
            <TextInput
              className="bg-gray-800 text-white rounded-xl px-4 py-3 mb-4"
              secureTextEntry
              value={current}
              onChangeText={setCurrent}
              placeholder="Enter current password"
              placeholderTextColor="#6b7280"
              autoCapitalize="none"
            />

            <Text className="text-gray-400 text-xs mb-1 ml-1">New Password</Text>
            <TextInput
              className="bg-gray-800 text-white rounded-xl px-4 py-3 mb-4"
              secureTextEntry
              value={next}
              onChangeText={setNext}
              placeholder="Min. 8 characters"
              placeholderTextColor="#6b7280"
              autoCapitalize="none"
            />

            <Text className="text-gray-400 text-xs mb-1 ml-1">Confirm New Password</Text>
            <TextInput
              className="bg-gray-800 text-white rounded-xl px-4 py-3 mb-8"
              secureTextEntry
              value={confirm}
              onChangeText={setConfirm}
              placeholder="Repeat new password"
              placeholderTextColor="#6b7280"
              autoCapitalize="none"
            />

            <TouchableOpacity
              onPress={handleSubmit}
              disabled={loading}
              className="bg-indigo-600 rounded-xl py-4 items-center"
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text className="text-white font-semibold text-base">
                  Update Password
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
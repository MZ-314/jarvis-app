import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../../hooks/useAuth";

export default function Login() {
  const router = useRouter();
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) return;
    await login(email.trim(), password);
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-background"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1 }}
        keyboardShouldPersistTaps="handled"
      >
        <View className="flex-1 justify-center px-8">
          {/* Logo / Title */}
          <View className="items-center mb-12">
            <Text className="text-primary text-6xl font-bold mb-2">J</Text>
            <Text className="text-text text-3xl font-bold">Jarvis</Text>
            <Text className="text-muted text-sm mt-1">AI Engineering Assistant</Text>
          </View>

          {/* Error */}
          {error && (
            <View className="bg-danger/20 border border-danger rounded-xl px-4 py-3 mb-6">
              <Text className="text-danger text-sm">{error}</Text>
            </View>
          )}

          {/* Inputs */}
          <View className="gap-4 mb-6">
            <TextInput
              className="bg-card border border-border rounded-xl px-4 py-4 text-text text-base"
              placeholder="Email"
              placeholderTextColor="#8888AA"
              keyboardType="email-address"
              autoCapitalize="none"
              value={email}
              onChangeText={setEmail}
            />
            <TextInput
              className="bg-card border border-border rounded-xl px-4 py-4 text-text text-base"
              placeholder="Password"
              placeholderTextColor="#8888AA"
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />
          </View>

          {/* Login Button */}
          <Pressable
            className="bg-primary rounded-xl py-4 items-center mb-4"
            onPress={handleLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="text-white font-semibold text-base">Sign In</Text>
            )}
          </Pressable>

          {/* Register Link */}
          <Pressable
            className="items-center py-2"
            onPress={() => router.push("/(auth)/register")}
          >
            <Text className="text-muted text-sm">
              Don't have an account?{" "}
              <Text className="text-primary font-semibold">Sign Up</Text>
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
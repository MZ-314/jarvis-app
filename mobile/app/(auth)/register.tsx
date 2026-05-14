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

export default function Register() {
  const router = useRouter();
  const { register, isLoading, error } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleRegister = async () => {
    setLocalError(null);
    if (!name.trim() || !email.trim() || !password.trim()) {
      setLocalError("All fields are required.");
      return;
    }
    if (password !== confirmPassword) {
      setLocalError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setLocalError("Password must be at least 8 characters.");
      return;
    }
    await register(name.trim(), email.trim(), password);
  };

  const displayError = localError ?? error;

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
          {/* Title */}
          <View className="items-center mb-12">
            <Text className="text-primary text-6xl font-bold mb-2">J</Text>
            <Text className="text-text text-3xl font-bold">Create Account</Text>
            <Text className="text-muted text-sm mt-1">Join Jarvis today</Text>
          </View>

          {/* Error */}
          {displayError && (
            <View className="bg-danger/20 border border-danger rounded-xl px-4 py-3 mb-6">
              <Text className="text-danger text-sm">{displayError}</Text>
            </View>
          )}

          {/* Inputs */}
          <View className="gap-4 mb-6">
            <TextInput
              className="bg-card border border-border rounded-xl px-4 py-4 text-text text-base"
              placeholder="Full Name"
              placeholderTextColor="#8888AA"
              autoCapitalize="words"
              value={name}
              onChangeText={setName}
            />
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
            <TextInput
              className="bg-card border border-border rounded-xl px-4 py-4 text-text text-base"
              placeholder="Confirm Password"
              placeholderTextColor="#8888AA"
              secureTextEntry
              value={confirmPassword}
              onChangeText={setConfirmPassword}
            />
          </View>

          {/* Register Button */}
          <Pressable
            className="bg-primary rounded-xl py-4 items-center mb-4"
            onPress={handleRegister}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="text-white font-semibold text-base">
                Create Account
              </Text>
            )}
          </Pressable>

          {/* Login Link */}
          <Pressable
            className="items-center py-2"
            onPress={() => router.back()}
          >
            <Text className="text-muted text-sm">
              Already have an account?{" "}
              <Text className="text-primary font-semibold">Sign In</Text>
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
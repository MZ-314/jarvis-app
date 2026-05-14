import { useState } from "react";
import { useRouter } from "expo-router";
import { authService } from "../services/authService";
import { useAuthStore } from "../store/authStore";

export function useAuth() {
  const router = useRouter();
  const { token, user, clearAuth } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await authService.register({ name, email, password });
      router.replace("/(main)/voice");
    } catch (e: any) {
      setError(e.message ?? "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await authService.login({ email, password });
      router.replace("/(main)/voice");
    } catch (e: any) {
      setError(e.message ?? "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    await clearAuth();
    router.replace("/(auth)/login");
  };

  return {
    token,
    user,
    isLoading,
    error,
    register,
    login,
    logout,
  };
}
import { create } from "zustand";
import * as SecureStore from "expo-secure-store";

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isHydrated: boolean;
  setAuth: (token: string, user: User) => Promise<void>;
  clearAuth: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isHydrated: false,

  setAuth: async (token, user) => {
    await SecureStore.setItemAsync("token", token);
    await SecureStore.setItemAsync("user", JSON.stringify(user));
    set({ token, user });
  },

  clearAuth: async () => {
    await SecureStore.deleteItemAsync("token");
    await SecureStore.deleteItemAsync("user");
    set({ token: null, user: null });
  },

  hydrate: async () => {
    try {
      const token = await SecureStore.getItemAsync("token");
      const userRaw = await SecureStore.getItemAsync("user");
      const user = userRaw ? JSON.parse(userRaw) : null;
      set({ token, user, isHydrated: true });
    } catch {
      set({ isHydrated: true });
    }
  },
}));
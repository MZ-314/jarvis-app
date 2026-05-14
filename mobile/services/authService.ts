import { api } from "./api";
import { useAuthStore } from "../store/authStore";

interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

interface LoginPayload {
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    username: string;
    full_name: string;
  };
}

export const authService = {
  register: async (payload: RegisterPayload) => {
    const data = await api.post<AuthResponse>("/auth/register", {
      full_name: payload.name,
      username: payload.email
        .split("@")[0]
        .toLowerCase()
        .replace(/[^a-z0-9]/g, ""),
      email: payload.email,
      password: payload.password,
    }, false);
    const user = { id: String(data.user.id), email: data.user.email, name: data.user.full_name ?? data.user.username };
    await useAuthStore.getState().setAuth(data.access_token, user);
    return data;
  },

  login: async (payload: LoginPayload) => {
    const data = await api.post<AuthResponse>("/auth/login", payload, false);
    const user = { id: String(data.user.id), email: data.user.email, name: data.user.full_name ?? data.user.username };
    await useAuthStore.getState().setAuth(data.access_token, user);
    return data;
  },

  logout: async () => {
    await useAuthStore.getState().clearAuth();
  },

  deleteAccount: async (password?: string) => {
    return api.post("/auth/me/delete", { password });
  },

  me: async () => {
    return api.get<{ user: AuthResponse["user"] }>("/auth/me");
  },
};
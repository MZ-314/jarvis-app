import { useAuthStore } from "../store/authStore";

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:5000") + "/api";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface RequestOptions {
  method?: Method;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (auth) {
    const token = useAuthStore.getState().token;
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? data.message ?? "Request failed");
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, auth = true) =>
    request<T>(endpoint, { method: "GET", auth }),

  post: <T>(endpoint: string, body: unknown, auth = true) =>
    request<T>(endpoint, { method: "POST", body, auth }),

  put: <T>(endpoint: string, body: unknown, auth = true) =>
    request<T>(endpoint, { method: "PUT", body, auth }),

  patch: <T>(endpoint: string, body: unknown, auth = true) =>
    request<T>(endpoint, { method: "PATCH", body, auth }),

  delete: <T>(endpoint: string, auth = true) =>
    request<T>(endpoint, { method: "DELETE", auth }),
};
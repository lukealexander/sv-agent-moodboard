import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Authenticated fetch wrapper. Pass accessToken from useAuth().
 * Throws on non-2xx responses.
 */
export async function fetchWithAuth<T>(
  path: string,
  accessToken: string | null,
  init?: RequestInit,
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`);
  }

  return response.json() as Promise<T>;
}

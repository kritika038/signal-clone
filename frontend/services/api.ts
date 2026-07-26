const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null;
  retrying?: boolean;
}

export async function apiRequest<T>(
  path: string,
  { token, headers, retrying = false, ...init }: RequestOptions = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  const payload = (await response.json().catch(() => null)) as
    | { success?: boolean; data?: T; error?: { message?: string } }
    | null;

  if (response.status === 401 && token && !retrying && typeof window !== "undefined") {
    const { useSessionStore } = await import("@/store/use-session-store");
    const sessionState = useSessionStore.getState();
    if (sessionState.refreshToken && sessionState.user && sessionState.sessionId) {
      const refreshResponse = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: sessionState.refreshToken }),
      });
      const refreshPayload = (await refreshResponse.json().catch(() => null)) as
        | { success?: boolean; data?: { access_token: string; refresh_token: string } }
        | null;
      if (refreshResponse.ok && refreshPayload?.data) {
        sessionState.setTokens({
          accessToken: refreshPayload.data.access_token,
          refreshToken: refreshPayload.data.refresh_token,
        });
        return apiRequest<T>(path, {
          ...init,
          headers,
          token: refreshPayload.data.access_token,
          retrying: true,
        });
      }
    }
    sessionState.clearSession();
  }

  if (!response.ok || payload?.success === false) {
    throw new ApiError(
      payload?.error?.message || "Something went wrong while contacting the server.",
      response.status
    );
  }

  return (payload?.data ?? payload) as T;
}

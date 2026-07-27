export const API_URL = (() => {
  let url = process.env.NEXT_PUBLIC_API_URL || "https://signal-clone-backend-xja6.onrender.com";
  if (url.endsWith("/api/v1")) url = url.slice(0, -7);
  if (url.endsWith("/api/v1/")) url = url.slice(0, -8);
  if (url.endsWith("/")) url = url.slice(0, -1);
  return url;
})();

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
  let response: Response;
  try {
    const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
    const computedHeaders: HeadersInit = {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    };

    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: computedHeaders,
    });
  } catch (error) {
    // This catches network errors and CORS errors (e.g. TypeError: Failed to fetch)
    throw new ApiError("Network error. The backend may be unreachable or blocked by CORS.", 0);
  }

  const payload = (await response.json().catch(() => null)) as
    | { success?: boolean; data?: T; error?: { message?: string }; detail?: any; message?: string }
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
    let errorMessage = "Something went wrong while contacting the server.";
    
    if (payload?.error?.message) {
      errorMessage = payload.error.message;
    } else if (payload?.detail) {
      // Handle FastAPI validation errors (422)
      if (Array.isArray(payload.detail) && payload.detail.length > 0) {
        errorMessage = payload.detail.map((err: any) => err.msg).join(", ");
      } else if (typeof payload.detail === "string") {
        errorMessage = payload.detail;
      }
    } else if (payload?.message) {
      errorMessage = payload.message;
    }

    throw new ApiError(errorMessage, response.status);
  }

  return (payload?.data ?? payload) as T;
}

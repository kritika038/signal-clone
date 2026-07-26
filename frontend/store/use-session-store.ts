"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { AuthSessionPayload, AuthUser } from "@/types/auth";

interface SessionState {
  accessToken: string | null;
  refreshToken: string | null;
  sessionId: string | null;
  user: AuthUser | null;
  setSession: (payload: AuthSessionPayload) => void;
  setTokens: (tokens: { accessToken: string; refreshToken: string }) => void;
  updateUser: (user: AuthUser) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      sessionId: null,
      user: null,
      setSession: (payload) =>
        set({
          accessToken: payload.tokens.access_token,
          refreshToken: payload.tokens.refresh_token,
          sessionId: payload.session_id,
          user: payload.user,
        }),
      setTokens: ({ accessToken, refreshToken }) =>
        set({
          accessToken,
          refreshToken,
        }),
      updateUser: (user) => set({ user }),
      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          sessionId: null,
          user: null,
        }),
    }),
    {
      name: "signal-session-store",
      storage: createJSONStorage(() => localStorage),
    }
  )
);

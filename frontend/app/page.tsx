"use client";

import { useSessionStore } from "@/store/use-session-store";

import { AuthScreen } from "@/features/auth/components/auth-screen";
import { SignalShell } from "@/features/chat/components/signal-shell";

export default function HomePage() {
  const accessToken = useSessionStore((state) => state.accessToken);

  if (!accessToken) {
    return <AuthScreen />;
  }

  return <SignalShell />;
}

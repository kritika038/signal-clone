"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useSessionStore } from "@/store/use-session-store";
import { fetchMe } from "@/services/auth";
import { Loader2 } from "lucide-react";

export function SessionRestorer({ children }: { children: React.ReactNode }) {
  const { accessToken, clearSession, updateUser } = useSessionStore();
  const [isInitializing, setIsInitializing] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let isMounted = true;

    async function initializeSession() {
      if (!accessToken) {
        if (isMounted) setIsInitializing(false);
        if (pathname !== "/login" && pathname !== "/") {
          router.push("/login");
        }
        return;
      }

      try {
        const user = await fetchMe(accessToken);
        if (isMounted) {
          updateUser(user);
          setIsInitializing(false);
          if (pathname === "/login") {
            router.push("/");
          }
        }
      } catch (error) {
        // If fetchMe fails (and refresh interceptor fails), clear session
        if (isMounted) {
          clearSession();
          setIsInitializing(false);
          if (pathname !== "/login" && pathname !== "/") {
            router.push("/login");
          }
        }
      }
    }

    initializeSession();

    return () => {
      isMounted = false;
    };
  }, [accessToken, pathname, router, clearSession, updateUser]);

  if (isInitializing) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center justify-center space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
          <p className="text-sm text-neutral-400 font-medium">Restoring session...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

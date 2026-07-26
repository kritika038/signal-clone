"use client";

import { useEffect, useState, useCallback } from "react";
import { getToken, onMessage } from "firebase/messaging";
import { getFirebaseMessaging, isFirebaseConfigured } from "@/lib/firebase";
import { registerDeviceToken } from "@/services/devices";
import { useSessionStore } from "@/store/use-session-store";

export function useFirebaseMessaging() {
  const [fcmToken, setFcmToken] = useState<string | null>(null);
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const { accessToken } = useSessionStore();

  const getOrCreateDeviceId = useCallback(() => {
    if (typeof window === "undefined") return "web-device";
    let deviceId = localStorage.getItem("signal_web_device_id");
    if (!deviceId) {
      deviceId = `web-${crypto.randomUUID()}`;
      localStorage.setItem("signal_web_device_id", deviceId);
    }
    return deviceId;
  }, []);

  const registerCurrentToken = useCallback(async () => {
    if (typeof window === "undefined" || !("Notification" in window) || !accessToken) {
      return;
    }

    try {
      const currentPermission = Notification.permission;
      setPermission(currentPermission);

      if (currentPermission !== "granted") return;

      const messaging = await getFirebaseMessaging();
      if (!messaging) return;

      const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
      const token = await getToken(messaging, {
        vapidKey: process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY,
        serviceWorkerRegistration: registration,
      }).catch((err) => {
        console.warn("FCM getToken failed:", err);
        return null;
      });

      if (token) {
        setFcmToken(token);
        const deviceId = getOrCreateDeviceId();
        await registerDeviceToken(
          {
            device_id: deviceId,
            platform: "web",
            fcm_token: token,
          },
          accessToken
        ).catch((err) => console.error("Failed to register device token with backend:", err));
      }
    } catch (error) {
      console.error("Error setting up Firebase Messaging:", error);
    }
  }, [accessToken, getOrCreateDeviceId]);

  const requestPermissionAndRegister = useCallback(async () => {
    if (typeof window === "undefined" || !("Notification" in window) || !accessToken) return;
    const requestedPermission = await Notification.requestPermission();
    setPermission(requestedPermission);
    if (requestedPermission === "granted") await registerCurrentToken();
  }, [accessToken, registerCurrentToken]);

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPermission(Notification.permission);
    }
    // Never show a permission prompt on page load. Browsers require a user
    // gesture and Signal asks from the Notifications settings panel instead.
    if (accessToken && "Notification" in window && Notification.permission === "granted") {
      void registerCurrentToken();
    }
  }, [accessToken, registerCurrentToken]);

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    if (!isFirebaseConfigured()) return undefined;
    getFirebaseMessaging().then((messaging) => {
      if (messaging) {
        unsubscribe = onMessage(messaging, (payload) => {
          console.log("[useFirebaseMessaging] Foreground message received:", payload);
          if ("Notification" in window && Notification.permission === "granted") {
            const title = payload.notification?.title || payload.data?.title || "New Message";
            const options = {
              body: payload.notification?.body || payload.data?.body,
              data: payload.data,
            };
            const notification = new Notification(title, options);
            notification.onclick = () => {
              window.focus();
              const conversationId = payload.data?.conversation_id;
              window.location.assign(conversationId ? `/?conversation_id=${encodeURIComponent(conversationId)}` : "/");
            };
          }
        });
      }
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);

  return { enabled: isFirebaseConfigured(), fcmToken, permission, requestPermissionAndRegister };
}

import { initializeApp, getApps, getApp } from "firebase/app";
import { getMessaging, isSupported, Messaging } from "firebase/messaging";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = () =>
  Boolean(
    firebaseConfig.apiKey &&
      firebaseConfig.authDomain &&
      firebaseConfig.projectId &&
      firebaseConfig.messagingSenderId &&
      firebaseConfig.appId &&
      process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY
  );

export const getFirebaseApp = () => {
  if (!isFirebaseConfigured()) return null;
  return getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
};

export const getFirebaseMessaging = async (): Promise<Messaging | null> => {
  if (typeof window === "undefined") return null;
  const supported = await isSupported().catch(() => false);
  if (!supported) return null;
  const app = getFirebaseApp();
  if (!app) return null;
  return getMessaging(app);
};

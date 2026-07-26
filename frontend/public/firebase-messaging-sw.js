/* eslint-disable no-undef */
importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js");
importScripts("/firebase-config.js");

if (!self.__FIREBASE_CONFIG__ || !self.__FIREBASE_CONFIG__.apiKey) {
  throw new Error("Firebase web configuration is missing.");
}

firebase.initializeApp(self.__FIREBASE_CONFIG__);

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log("[firebase-messaging-sw.js] Received background message ", payload);
  const notificationTitle = payload.notification?.title || payload.data?.title || "New Message";
  const notificationOptions = {
    body: payload.notification?.body || payload.data?.body || "You have a new message",
    icon: "/icon.png",
    data: payload.data || {},
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const conversationId = event.notification.data?.conversation_id;
  const targetUrl = conversationId ? `/?conversation_id=${encodeURIComponent(conversationId)}` : "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.startsWith(self.location.origin) && "focus" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

# Signal Clone

Production-oriented Signal-style messaging platform built with FastAPI, Socket.IO, SQLAlchemy 2, Next.js, and Flutter with Firebase Cloud Messaging (FCM).

## Architecture

- **Backend**: FastAPI with clean architecture split across `api`, `services`, `repositories`, `models`, and `websocket`.
- **Database**: PostgreSQL (staging/production) or SQLite (development/testing).
- **Caching & Rate Limiting**: Redis-backed infrastructure with fallback to in-memory mode.
- **Storage**: Abstracted behind `StorageProvider` with local, MinIO, S3, and Cloudflare R2 support.
- **Background Jobs**: Scheduler abstraction supporting `AsyncScheduler`, Celery, and Dramatiq.
- **Push Notifications**: Firebase Cloud Messaging (FCM) integrated via `NotificationService` and `FirebaseNotificationProvider` with device token management and fallback to `MockNotificationProvider`.
- **Frontend (Web)**: Next.js with TypeScript, TailwindCSS, Zustand, TanStack Query, Socket.IO client, and Firebase Web Push SDK.
- **Mobile (Flutter)**: Flutter client supporting `firebase_core`, `firebase_messaging`, local notifications, token refresh, and background/killed state deep-linking.

---

## Firebase Cloud Messaging (FCM) Integration

Firebase is used **exclusively for Push Notifications**. Authentication remains managed by the FastAPI backend JWT system, and data storage remains in PostgreSQL.

### Firebase Setup & Service Account

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Create a new Firebase project (e.g., `signal-clone-app`).
3. Under **Project Settings** > **Service Accounts**, click **Generate new private key** to download the JSON credentials file.
4. Set `FIREBASE_CREDENTIALS_PATH=/path/to/service-account.json` or `FIREBASE_CREDENTIALS_JSON='{...}'` in your environment.
5. Set `NOTIFICATION_BACKEND=firebase` to enable live FCM notifications. When omitted or `NOTIFICATION_BACKEND=mock`, the system operates in mock/test mode.

### Web Configuration (Next.js)

1. In Firebase Console, add a Web App under Project Settings.
2. Under **Web Push Certificates** (VAPID key), generate a key pair.
3. Configure frontend environment variables in `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=signal-clone
   NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
   NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   NEXT_PUBLIC_FIREBASE_VAPID_KEY=your_vapid_key
   ```
4. The service worker at `frontend/public/firebase-messaging-sw.js` handles background notifications and chat deep-linking. Its public Firebase configuration is served dynamically by `frontend/app/firebase-config.js/route.ts`; do not put service-account credentials in frontend environment variables.
5. In Signal Web, open **Settings → Notifications** and choose **Enable browser notifications**. The browser prompt is intentionally only shown after that user action.

### Android Configuration (Flutter)

1. Add your Android App package name (e.g. `com.signal.clone`) in Firebase Console.
2. Download `google-services.json` and place it in `mobile/android/app/google-services.json`.
3. Build the APK: `cd mobile && flutter build apk`.
4. Run against the existing backend with `flutter run --dart-define=SIGNAL_API_URL=https://api.example.com`. The authenticated application shell must pass its FastAPI JWT to `FCMService.initialize`; Firebase Authentication is not used.

### iOS Configuration (Flutter)

1. Add your iOS App Bundle ID in Firebase Console.
2. Download `GoogleService-Info.plist` and place it in `mobile/ios/Runner/GoogleService-Info.plist`.
3. Upload your APNs Authentication Key (.p8) in Firebase Console under **Project Settings** > **Cloud Messaging**.

---

## Environment Variables

### Backend Environment Variables

- `ENVIRONMENT`: `development`, `testing`, `staging`, `production`
- `DATABASE_BACKEND`: `sqlite`, `postgresql`
- `DATABASE_URL`: optional explicit database connection string
- `REDIS_BACKEND`: `memory`, `redis`
- `REDIS_URL`: Redis connection string (e.g. `redis://localhost:6379/0`)
- `NOTIFICATION_BACKEND`: `mock`, `firebase`, `apns`
- `FIREBASE_PROJECT_ID`: Firebase project ID
- `FIREBASE_CREDENTIALS_PATH`: File path to service account JSON key
- `FIREBASE_CREDENTIALS_JSON`: Raw JSON contents of service account key
- `NEXT_PUBLIC_FIREBASE_*`: web app's public Firebase configuration (set in `frontend/.env.local`, never use service-account values)
- `NEXT_PUBLIC_FIREBASE_VAPID_KEY`: web-push VAPID key
- `SIGNAL_API_URL`: Flutter build-time backend base URL

---

## Device Registration APIs

- **`POST /api/v1/devices/register`**: Registers or updates an FCM device token.
  ```json
  {
    "device_id": "unique-device-identifier",
    "platform": "ios | android | web",
    "fcm_token": "fcm_token_string"
  }
  ```
- **`GET /api/v1/devices`**: Returns a list of active device tokens for the authenticated user.
- **`DELETE /api/v1/devices/{device_id}`**: Deletes the specified device token for the current user.

---

## Database and Migrations

Run database migrations:

```bash
cd backend
alembic upgrade head
```

---

## Docker

Run local stack:

```bash
docker compose up --build
```

Run production stack:

```bash
docker compose -f docker-compose.prod.yml up --build
```

---

## Verification and Testing

### Backend Verification

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests
python3 -m compileall app
```

### Frontend Verification

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

---

## Manual Testing Steps

1. **Register Device Token**: Send a `POST /api/v1/devices/register` request with JWT header to register a device.
2. **List Registered Devices**: Verify devices via `GET /api/v1/devices`.
3. **Web Permission**: In the web app, enable notifications from Settings and verify the device registration appears in `GET /api/v1/devices`.
4. **Send Message**: Send a direct message, group message, mention, reply, or group invite and verify FCM delivery. Sender is automatically excluded.
5. **Invalid Token Cleanup**: If FCM returns `UnregisteredError`, invalid tokens are automatically purged from PostgreSQL.
6. **Deep Link**: Tap a background/terminated mobile notification or a web notification and verify it opens the supplied conversation.
7. **Delete Device**: Call `DELETE /api/v1/devices/{device_id}` and verify device removal.

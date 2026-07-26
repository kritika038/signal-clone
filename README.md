# Signal Clone

A production-grade, secure messaging application inspired by Signal.

## Features

- **End-to-End Style Registration:** Secure onboarding with email OTP verification.
- **Production-Grade Auth:** Rate limiting, secure session management, single-use hashed OTPs, and strict expiration rules.
- **Real-Time Messaging:** WebSockets with Socket.IO for instant message delivery, read receipts, and typing indicators.
- **Media Support:** Upload images, videos, and documents to cloud storage (S3 compatible).
- **Responsive UI:** Dark mode, smooth Framer Motion animations, skeletons, and polished design.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), Alembic, SQLite (or PostgreSQL), WebSockets (python-socketio).
- **Frontend:** Next.js 14, React, Tailwind CSS, Framer Motion, TanStack Query, Zustand.
- **Services:** SMTP/Resend/Mailtrap for emails, AWS S3 / MinIO for object storage.

## Getting Started

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment and local setup instructions.
See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture, ER diagrams, and socket flow.

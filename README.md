<div align="center">

# 💬 Secure Messaging Platform (Signal Clone)

*A full-stack, scalable messaging platform replicating the modern Signal Messenger experience.*

[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-010101?style=for-the-badge&logo=socket.io&logoColor=white)](https://socket.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=json-web-tokens&logoColor=white)](https://jwt.io/)

**[Live Application (Vercel)](https://signal-clone-r4hxsfh8u-kritikas-projects-85137cfb.vercel.app/)** • **[Live API (Render)](https://signal-clone-backend-xja6.onrender.com)** • **[GitHub Repository](https://github.com/kritika038/signal-clone)**

</div>

---

## 🚀 Live Demo & Test Accounts

You can test the application live without installing it locally:
- **Frontend URL:** [https://signal-clone-r4hxsfh8u-kritikas-projects-85137cfb.vercel.app/](https://signal-clone-hzmyyx7qq-kritikas-projects-85137cfb.vercel.app/)

**Demo Accounts (OTP is always `123456`):**
- Phone: `+1234567890`

---

## 📖 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Database Schema](#database-schema)
- [Real-Time Events](#real-time-events)
- [Security, Performance & Scalability](#security-performance--scalability)
- [Installation & Local Setup](#installation--local-setup)
- [API Documentation](#api-documentation)
- [Assignment Mapping](#assignment-mapping)
- [Final Notes](#final-notes)

---

<a id="project-overview"></a>
## 🎯 Project Overview

This project was built to address the complexities of modern real-time communication by replicating the user experience and architectural demands of **Signal Messenger**.

**Why this exists:** The goal of this project is to demonstrate mastery over full-stack web development, specifically tackling challenges like real-time state synchronization, optimistic UI updates, resilient socket connections, and scalable backend design.

**Implementation Scope:**
- Recreates the **Signal Desktop** UI/UX with pixel-perfect attention to detail (dark mode, typography, layouts).
- Focuses heavily on **Scalable Architecture** (FastAPI, Redis, SQLAlchemy) and **Real-Time Delivery** (Socket.IO).
- E2E Encryption is *mocked*, as the primary objective of this assignment is architectural design, database modeling, and real-time frontend/backend integration, not cryptographic implementation.

---

<a id="features"></a>
## ✨ Features

### 🔐 Authentication
- [x] Phone/Username Registration & Login
- [x] Mock OTP Verification (Demo OTP: `123456`)
- [x] Secure JWT Authentication with Refresh Tokens
- [x] Profile Avatar & Display Name Setup
- [x] Persistent Sessions & Session Rotation

### 💬 Messaging
- [x] One-to-One Direct Chat
- [x] Real-time Sub-millisecond Messaging
- [x] Typing Indicators (with auto-hide)
- [x] Read Receipts (Sent, Delivered, Read)
- [x] Message History & Infinite Scroll
- [x] Media Uploads (Images, Videos, Files)
- [x] Disappearing Messages

### 👥 Group Messaging
- [x] Group Creation with Avatars
- [x] Admin Controls (Transfer Ownership)
- [x] Member Management (Add/Remove/Leave)
- [x] Real-time Group Chat synchronization

### 🟢 Presence & Notifications
- [x] Online/Offline/Away Status
- [x] Last Seen timestamps
- [x] Toast Notifications for incoming messages

### 🎨 UI / UX
- [x] Signal Desktop responsive layout
- [x] Deep Dark Mode
- [x] Settings & Profile Modal
- [x] Global Contact Search
- [x] Optimistic UI for instantaneous message sending

---

<a id="tech-stack"></a>
## 🛠 Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 15, React, TypeScript, Tailwind CSS |
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic |
| **Database** | PostgreSQL (Async), Redis (Pub/Sub & Caching) |
| **Realtime** | Socket.IO (python-socketio, socket.io-client) |
| **State Management**| Zustand, TanStack React Query |
| **Authentication** | JWT (JSON Web Tokens), bcrypt |

---

<a id="screenshots"></a>
## 📸 Screenshots

<details>
<summary><b>Authentication & Registration</b></summary>
<br>
<img src="docs/images/auth-screen.png" alt="Authentication Screen" width="800">
</details>

<details>
<summary><b>Conversation List & Main Layout</b></summary>
<br>
<img src="docs/images/main-layout.png" alt="Main Layout" width="800">
</details>

<details>
<summary><b>Real-Time Chat & Emoji</b></summary>
<br>
<img src="docs/images/chat-screen.png" alt="Chat Screen" width="800">
</details>

<details>
<summary><b>Group Management</b></summary>
<br>
<img src="docs/images/group-management.png" alt="Group Management" width="800">
</details>

---

<a id="architecture"></a>
## 🏗 Architecture

The application follows a modular, horizontally scalable architecture.

```mermaid
graph TD
    Client[Next.js Client] -->|HTTPS REST| API[FastAPI Gateway]
    Client <-->|WebSocket w/ Polling Fallback| SocketIO[Socket.IO Server]
    
    API --> Auth[Auth Service]
    API --> Msg[Message Service]
    API --> Media[Media Service]
    
    SocketIO -->|Pub/Sub| Redis[(Redis)]
    
    Auth --> DB[(PostgreSQL)]
    Msg --> DB
    Media --> S3[Storage / Local]
```

### Layer Breakdown
- **Next.js Client**: Utilizes TanStack Query for server-state caching and Zustand for client-side state. Optimistically updates the UI before server confirmation.
- **FastAPI Gateway**: Handles HTTP requests, validation (Pydantic v2), and authentication via dependency injection.
- **Socket.IO Server**: Manages stateful WebSocket connections. Connects to Redis as a message broker to allow horizontal scaling (multiple Socket.IO workers).
- **PostgreSQL**: The primary source of truth, interacted with asynchronously via SQLAlchemy.

---

<a id="folder-structure"></a>
## 📂 Folder Structure

```text
signal-clone/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/routes/       # FastAPI endpoints (auth, messages, groups)
│   │   ├── core/             # Config, security, exceptions
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # Database access layer
│   │   ├── schemas/          # Pydantic v2 validation schemas
│   │   ├── services/         # Business logic layer
│   │   └── websocket/        # Socket.IO event handlers and rooms
│   ├── main.py               # Application entry point
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # Reusable UI components
│   ├── features/             # Feature-based architecture (auth, chat)
│   ├── hooks/                # Custom React hooks
│   ├── services/             # API and Socket.IO clients
│   ├── store/                # Zustand global stores
│   └── tailwind.config.ts    
└── README.md
```

---

<a id="database-schema"></a>
## 🗄 Database Schema

```mermaid
erDiagram
    User ||--o{ UserSession : has
    User ||--o{ ConversationMember : participates_in
    User ||--o{ Message : sends
    User ||--o{ Contact : saves
    
    Conversation ||--o{ ConversationMember : contains
    Conversation ||--o{ Message : contains
    
    Message ||--o{ Attachment : includes
    Message ||--o{ MessageReceipt : tracked_by
    Message ||--o{ Reaction : receives
```

- **User**: Core identity, presence status, and encrypted password hash.
- **Conversation**: Can be `DIRECT` (1-on-1) or `GROUP`. Tracks `last_activity_at` for sorting.
- **Message**: Stores content, reply relations, and soft deletion flags.
- **MessageReceipt**: Tracks `SENT`, `DELIVERED`, and `READ` status per user per message.

---

<a id="real-time-events"></a>
## ⚡ Real-Time Events

The application uses Socket.IO namespaces to handle real-time events efficiently.

| Event Name | Direction | Description |
|------------|-----------|-------------|
| `connect` | Client ➡️ Server | Authenticates connection using JWT. |
| `message.send` | Client ➡️ Server | Emits a new message to the room. |
| `message.received` | Server ➡️ Client | Broadcasts message to room participants. |
| `typing.start` | Client ↔️ Server | Broadcasts that a user is typing. |
| `receipt.update` | Client ↔️ Server | Broadcasts read/delivery receipts. |
| `presence.update`| Server ➡️ Client | Notifies clients when a user comes online/offline. |

---

<a id="security-performance--scalability"></a>
## 🔒 Security, Performance & Scalability

### Security
- **Authentication**: JWT access and refresh tokens. Passwords hashed via `bcrypt`.
- **Validation**: Strict input validation and sanitization using Pydantic v2. Phone numbers enforced via E.164 standard.
- **Middleware**: Global exception handlers prevent stack traces from leaking. `SecurityHeadersMiddleware` sets CSP, HSTS, and X-Frame-Options.

### Performance
- **Optimistic UI**: Messages appear instantly in the UI while the API request is in flight. Failures automatically rollback the UI state and show retry options.
- **Async Database**: Fully asynchronous database operations (`sqlalchemy.ext.asyncio`) prevent blocking the event loop.
- **Lazy Loading**: Relationships are eager-loaded only when necessary (`selectinload`) to prevent N+1 query problems.

### Scalability
- **Stateless API**: FastAPI routes are entirely stateless, allowing horizontal scaling behind a load balancer.
- **Redis Pub/Sub**: Socket.IO is configured with a Redis adapter, enabling seamless real-time communication across multiple server instances.

---

<a id="installation--local-setup"></a>
## ⚙️ Installation & Local Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL

### 1. Clone the Repository
```bash
git clone https://github.com/kritika038/signal-clone.git
cd signal-clone
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Set up environment variables
cp .env.example .env.local

# Start the development server
npm run dev
```

### Environment Variables

**Backend (`.env`)**
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@localhost:5432/signal`)
- `SECRET_KEY`: JWT signing key
- `ALGORITHM`: JWT algorithm (e.g., `HS256`)

**Frontend (`.env.local`)**
- `NEXT_PUBLIC_API_URL`: Backend URL (e.g., `http://localhost:8000`)

---

<a id="api-documentation"></a>
## 📚 API Documentation

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Register a new user | ❌ |
| `POST` | `/api/v1/auth/login/verify` | Verify OTP and login | ❌ |
| `GET`  | `/api/v1/auth/me` | Get current user profile | ✅ |
| `GET`  | `/api/v1/conversations` | List all user conversations | ✅ |
| `POST` | `/api/v1/conversations/{id}/messages`| Send a message | ✅ |
| `GET`  | `/api/v1/conversations/{id}/messages`| Get message history | ✅ |
| `POST` | `/api/v1/media/upload` | Upload media attachment | ✅ |

*(Interactive Swagger documentation available at `/docs` when running the backend).*

---

<a id="assignment-mapping"></a>
## 📋 Assignment Mapping

| Assignment Requirement | Status | Implementation Details |
|------------------------|--------|------------------------|
| **Authentication** | ✅ | Implemented JWT Auth, OTP Verification, Session Rotation |
| **Conversations** | ✅ | 1-on-1 and Group chats, Conversation list with unread counts |
| **Messaging** | ✅ | Text, Emojis, Attachments, Edit, Delete, Disappearing Messages |
| **Groups** | ✅ | Group creation, Admin management, Member tracking |
| **Signal UI** | ✅ | Pixel-perfect replication of Signal Desktop UI/UX, Dark mode |
| **Realtime** | ✅ | Socket.IO for messages, typing indicators, presence, receipts |
| **Persistence** | ✅ | PostgreSQL via async SQLAlchemy, Alembic migrations |
| **Responsive** | ✅ | Tailwind CSS used for desktop and mobile responsiveness |
| **Bonus Features** | ✅ | Comprehensive FastAPI Exception Middleware & Frontend Toasts |

---

<a id="final-notes"></a>
## 🏆 Final Notes

This repository was designed as a capstone project for a Full Stack Software Development Engineering (SDE) evaluation. 

It highlights the ability to:
- Design a **clean, modular backend architecture** utilizing dependency injection and repository patterns.
- Build a **resilient real-time engine** capable of scaling horizontally.
- Engineer a **sophisticated frontend state management** system using React Query and Zustand to handle complex asynchronous operations seamlessly.
- Write **production-grade code** that anticipates edge cases (e.g., token reuse attacks, race conditions, lazy-loading exceptions).

### License
This project is licensed under the MIT License.

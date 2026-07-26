# Deployment Guide

## Prerequisites
- Node.js 18+
- Python 3.11+
- SQLite or PostgreSQL
- A provider for Email (Gmail SMTP App Password, Resend API Key, or Mailtrap API Key)

## Environment Variables

### Backend `.env`

```
DATABASE_URL=sqlite+aiosqlite:///./signal_clone.db
# Or PostgreSQL: postgresql+asyncpg://user:pass@host/dbname

SECRET_KEY=your_super_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email Setup
EMAIL_PROVIDER=smtp  # 'smtp', 'resend', or 'mailtrap'

# If using SMTP (Gmail):
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com

# If using Resend:
RESEND_API_KEY=re_123456789

# If using Mailtrap:
MAILTRAP_API_KEY=mt_123456789
```

### Frontend `.env.local`

```
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api/v1
NEXT_PUBLIC_SOCKET_URL=https://your-backend-domain.com
```

## Local Development

1. **Backend**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Production Deployment (Render + Vercel)

### Backend (Render)
1. Create a new Web Service on Render.
2. Link the repository.
3. Root Directory: `backend`
4. Build Command: `pip install -r requirements.txt && alembic upgrade head`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add the environment variables above.

### Frontend (Vercel)
1. Create a new Project on Vercel.
2. Link the repository.
3. Root Directory: `frontend`
4. Framework Preset: `Next.js`
5. Add the `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SOCKET_URL` pointing to your Render backend.
6. Deploy.

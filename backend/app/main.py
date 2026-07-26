from __future__ import annotations

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.routes import auth, contacts, conversations, devices, drafts, groups, media, messages, notifications, search
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.services.health_service import health_service
from app.services.metrics_service import metrics_service
from app.services.runtime import runtime_services
from app.websocket.connection_manager import connection_manager
from app.websocket.manager import sio


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.disappearing_message_service import DisappearingMessageService
    from app.services.scheduled_message_service import ScheduledMessageService

    configure_logging()
    runtime_services.scheduler.add_recurring_job(
        "scheduled_messages",
        10.0,
        ScheduledMessageService().process_due_messages,
    )
    runtime_services.scheduler.add_recurring_job(
        "disappearing_messages",
        10.0,
        DisappearingMessageService().purge_expired_messages,
    )
    await runtime_services.scheduler.start()
    yield
    await runtime_services.scheduler.stop()


def create_app() -> socketio.ASGIApp:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else []
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app" if not cors_origins and settings.is_production else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)
    app.include_router(auth.router, prefix=settings.API_V1_STR)
    app.include_router(contacts.router, prefix=settings.API_V1_STR)
    app.include_router(conversations.router, prefix=settings.API_V1_STR)
    app.include_router(media.router, prefix=settings.API_V1_STR)
    app.include_router(media.upload_router, prefix=settings.API_V1_STR)
    app.include_router(drafts.router, prefix=settings.API_V1_STR)
    app.include_router(messages.router, prefix=settings.API_V1_STR)
    app.include_router(groups.router, prefix=settings.API_V1_STR)
    app.include_router(notifications.router, prefix=settings.API_V1_STR)
    app.include_router(devices.router, prefix=settings.API_V1_STR)
    app.include_router(search.router, prefix=settings.API_V1_STR)


    @app.get("/", tags=["System"])
    async def root():
        return {
            "success": True,
            "message": f"{settings.PROJECT_NAME} is running",
            "docs": "/docs",
            "health": "/live",
            "openapi": "/openapi.json"
        }

    @app.get("/health", tags=["System"])
    async def health_check():
        return {"success": True, "data": await health_service.health()}

    @app.get("/live", tags=["System"])
    async def live_check():
        return {"success": True, "data": await health_service.live()}

    @app.get("/ready", tags=["System"])
    async def ready_check():
        return {"success": True, "data": await health_service.ready()}

    @app.get("/metrics", tags=["System"])
    async def metrics():
        metrics_service.set_active_users(connection_manager.get_all_active_users())
        metrics_service.set_active_sockets(connection_manager.get_active_socket_count())
        return {"success": True, "data": metrics_service.snapshot()}

    return socketio.ASGIApp(sio, other_asgi_app=app)


app = create_app()

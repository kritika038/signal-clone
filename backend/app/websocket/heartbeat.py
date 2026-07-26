import asyncio
import logging
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)

async def heartbeat_cleanup_loop(interval_seconds: float = 30.0, timeout_seconds: float = 45.0):
    """
    Background loop checking for stale connection heartbeats.
    """
    logger.info("[WS Heartbeat] Initiated connection cleanup background task")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            stale_sockets = connection_manager.get_stale_sockets(timeout_seconds)
            if stale_sockets:
                logger.info(f"[WS Heartbeat] Found {len(stale_sockets)} stale socket connection(s), disconnecting...")
                from app.websocket.manager import sio
                for sid in stale_sockets:
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        logger.warning(f"[WS Heartbeat] Error disconnecting stale socket {sid}: {str(e)}")
                        # Force clean connection manager mapping in case disconnect callback fails
                        connection_manager.disconnect(sid)
        except asyncio.CancelledError:
            logger.info("[WS Heartbeat] Background task cancelled")
            break
        except Exception as e:
            logger.error(f"[WS Heartbeat] Exception in background loop: {str(e)}")

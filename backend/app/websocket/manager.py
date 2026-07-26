import socketio
import logging
import uuid
from typing import Dict, Any, Optional

from app.websocket.auth import authenticate_socket
from app.websocket.gateway import ws_gateway
from app.websocket.heartbeat import heartbeat_cleanup_loop

logger = logging.getLogger(__name__)

# Create Socket.IO server with CORS enabled for frontend
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

# Tracks if the heartbeat background loop has been started
heartbeat_task_started = False

# Socket.IO Event Hooks
@sio.event
async def connect(sid, environ, auth=None):
    """
    Validates connection token and delegates registration to ws_gateway.
    """
    global heartbeat_task_started
    if not heartbeat_task_started:
        sio.start_background_task(heartbeat_cleanup_loop)
        heartbeat_task_started = True

    result = await authenticate_socket(auth)
    if not result:
        logger.warning(f"[WS Connection] Authentication failed for sid {sid}. Connection rejected.")
        return False

    user, session = result
    await ws_gateway.handle_connect(sid, user.id)
    return True

@sio.event
async def disconnect(sid):
    """
    Cleans up socket mappings in ws_gateway.
    """
    await ws_gateway.handle_disconnect(sid)

@sio.on("heartbeat")
async def on_heartbeat(sid, data=None):
    await ws_gateway.handle_heartbeat(sid)

@sio.on("message.send")
async def on_message_send(sid, data):
    await ws_gateway.handle_message_send(sid, data)

@sio.on("message.edit")
async def on_message_edit(sid, data):
    await ws_gateway.handle_message_edit(sid, data)

@sio.on("message.delete")
async def on_message_delete(sid, data):
    await ws_gateway.handle_message_delete(sid, data)

@sio.on("message.delivered")
async def on_message_delivered(sid, data):
    await ws_gateway.handle_receipt_delivered(sid, data)

@sio.on("message.read")
async def on_message_read(sid, data):
    await ws_gateway.handle_receipt_read(sid, data)

@sio.on("typing.start")
async def on_typing_start(sid, data):
    await ws_gateway.handle_typing_start(sid, data)

@sio.on("typing.stop")
async def on_typing_stop(sid, data):
    await ws_gateway.handle_typing_stop(sid, data)

@sio.on("presence.update")
async def on_presence_update(sid, data):
    await ws_gateway.handle_presence_update(sid, data)

@sio.on("reaction.toggle")
async def on_reaction_toggle(sid, data):
    await ws_gateway.handle_reaction_toggle(sid, data)

class CompatibilityWebSocketManager:
    """
    Compatibility wrapper for components/tests that expect the old ws_manager interface.
    """
    async def connect(self, sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, Any]] = None) -> bool:
        return await connect(sid, environ, auth)
    
    async def disconnect(self, sid: str) -> None:
        await ws_gateway.handle_disconnect(sid)
        
    async def send_to_user(self, user_id: str, event: str, data: Any) -> bool:
        room = f"user:{user_id}"
        await sio.emit(event, data, to=room)
        return True

    async def broadcast(self, event: str, data: Any) -> None:
        await sio.emit(event, data)

ws_manager = CompatibilityWebSocketManager()

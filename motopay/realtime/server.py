"""Socket.IO server with Redis Pub/Sub bridge."""
from __future__ import annotations

import json
import threading
from typing import Any

import socketio

from motopay.config import get_settings
from motopay.domain.enums import UserRole
from motopay.observability.logger import get_logger
from motopay.realtime.publish import PLATFORM_CHANNEL
from motopay.services.auth_service import decode_token

logger = get_logger(__name__)

_sio: socketio.AsyncServer | None = None
_listener_started = False


def get_sio() -> socketio.AsyncServer:
    global _sio
    if _sio is None:
        settings = get_settings()
        mgr = socketio.AsyncRedisManager(settings.redis_url)
        _sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            client_manager=mgr,
            logger=False,
            engineio_logger=False,
        )
        _register_events(_sio)
    return _sio


def _register_events(sio: socketio.AsyncServer) -> None:
    @sio.event
    async def connect(sid: str, environ: dict, auth: dict | None) -> bool:
        token = (auth or {}).get("token") if auth else None
        if not token:
            logger.warning("Socket connect rejected: missing token sid=%s", sid)
            return False
        try:
            data = decode_token(token)
            role = UserRole(data["role"])
            operacao_id = data.get("operacao_id")
            await sio.save_session(
                sid,
                {
                    "user_id": int(data["sub"]),
                    "role": role.value,
                    "operacao_id": int(operacao_id) if operacao_id is not None else None,
                },
            )
            await sio.enter_room(sid, PLATFORM_CHANNEL)
            if role == UserRole.ADMIN:
                await sio.enter_room(sid, "admin")
            if operacao_id is not None:
                await sio.enter_room(sid, f"events:operacao:{operacao_id}")
            return True
        except Exception as exc:
            logger.warning("Socket connect rejected sid=%s: %s", sid, exc)
            return False

    @sio.event
    async def disconnect(sid: str) -> None:
        logger.debug("Socket disconnected sid=%s", sid)


def _redis_listener_thread() -> None:
    import asyncio

    from motopay.infrastructure.redis_client import get_redis_connection

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sio = get_sio()
    r = get_redis_connection()
    pubsub = r.pubsub()
    pubsub.psubscribe("events:*")
    logger.info("Realtime Redis listener started")

    async def _emit(event_type: str, data: dict, room: str) -> None:
        await sio.emit(event_type, data, room=room)

    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not message or message.get("type") not in ("message", "pmessage"):
            continue
        try:
            raw = message["data"]
            if isinstance(raw, bytes):
                raw = raw.decode()
            payload = json.loads(raw)
            event_type = payload.get("type", "event")
            data = payload.get("payload", {})
            channel = message.get("channel") or message.get("pattern") or PLATFORM_CHANNEL
            if isinstance(channel, bytes):
                channel = channel.decode()
            loop.run_until_complete(_emit(event_type, data, room=channel))
        except Exception as exc:
            logger.error("Realtime listener error: %s", exc)


def start_realtime_listener() -> None:
    global _listener_started
    if _listener_started:
        return
    _listener_started = True
    threading.Thread(target=_redis_listener_thread, daemon=True, name="realtime-redis").start()


def mount_realtime(app: Any) -> Any:
    get_sio()
    start_realtime_listener()
    return socketio.ASGIApp(get_sio(), other_asgi_app=app)

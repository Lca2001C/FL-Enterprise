"""ASGI entrypoint with Socket.IO mounted."""
from motopay.interfaces.api.main import app as fastapi_app
from motopay.realtime.server import mount_realtime

app = mount_realtime(fastapi_app)

"""
client_app/routes/stream.py — SSE relay for the client browser.

The client app maintains a persistent SSE connection to the central
server at /api/stream/client/<client_id>.  This route re-streams those
events to the browser so the dashboard updates live without a page refresh.
"""
import json

import requests as http

from flask import Blueprint, Response, current_app, stream_with_context

from client_app.client_state import state
from client_app.services.sync_service import SyncService

client_stream_bp = Blueprint("client_stream", __name__)


def _relay_generator():
    """
    Open a persistent SSE connection to the central server and relay
    every event to the browser.  Incoming 'transaction' events are also
    written to local SQLite via SyncService.
    """
    client_id  = current_app.config["CLIENT_ID"]
    server_url = current_app.config["SERVER_URL"]
    token      = state.jwt_token or ""

    url = f"{server_url}/api/stream/client/{client_id}?token={token}"

    try:
        with http.get(url, stream=True, timeout=None, headers=state.auth_headers(), verify=False) as resp:
            for line in resp.iter_lines():
                if not line:
                    # blank line — SSE boundary, forward keep-alive
                    yield "\n"
                    continue

                decoded = line.decode("utf-8") if isinstance(line, bytes) else line

                # Parse and intercept 'transaction' events to save locally
                if decoded.startswith("data:"):
                    try:
                        payload = json.loads(decoded[5:].strip())
                        if payload.get("type") == "transaction":
                            SyncService.save_transaction(payload.get("data", {}), direction="received")
                    except Exception:
                        pass  # parsing failure — just relay as-is

                yield decoded + "\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"


@client_stream_bp.route("/stream")
def stream():
    """
    Browser-facing SSE endpoint.
    The client dashboard connects here; this relays from the server.
    """
    if not state.is_authenticated():
        return Response("data: {\"error\": \"not authenticated\"}\n\n",
                        content_type="text/event-stream", status=401)

    return Response(
        stream_with_context(_relay_generator()),
        content_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )

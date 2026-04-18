"""
SSE stream routes — real-time event streaming to dashboard clients.

Endpoints:
    GET /api/stream/transactions  — SSE stream of new transaction events (JWT protected)
    GET /api/stream/status        — SSE stream of node status / peer changes (JWT protected)
"""
import json
import queue

from flask import Blueprint, Response, current_app, g, request, stream_with_context
from flask_jwt_extended import decode_token

from app.services.event_bus import EventBus
from app.services.notification_service import NotificationService
from app.utils.auth_helpers import token_required
from functools import wraps
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.models.account import Account
from app import db

stream_bp = Blueprint("stream", __name__)


def query_token_required(fn):
    """
    Verify Bearer JWT for SSE endpoints.
    EventSource can't set headers, so we accept the token as a ?token= query param.
    Decoded claims are stored in flask.g for downstream use.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.args.get("token") or ""
        if not token:
            # Also try the Authorization header as a fallback
            auth = request.headers.get("Authorization", "")
            token = auth.removeprefix("Bearer ").strip()
        if not token:
            from flask import jsonify
            return jsonify({"error": "Missing token"}), 401
        try:
            claims = decode_token(token)
            g.jwt_claims = claims  # cache for downstream routes
        except Exception as exc:
            from flask import jsonify
            return jsonify({"error": "Invalid token", "detail": str(exc)}), 401
        return fn(*args, **kwargs)
    return wrapper



def _format_sse(data: dict, event: str = "message") -> str:
    """Format a dict as a Server-Sent Event string."""
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_generator(event_type: str = "transaction"):
    """Generator that yields SSE-formatted events from the EventBus."""
    q = EventBus.subscribe()
    try:
        # Send an immediate "connected" heartbeat
        yield _format_sse({"type": "connected", "subscribers": EventBus.subscriber_count()}, "status")

        while True:
            try:
                event = q.get(timeout=20)
                # Only forward events of the requested type (or all)
                if event_type == "all" or event.get("type") == event_type:
                    yield _format_sse(event, event.get("type", "message"))
            except queue.Empty:
                # Send a keep-alive comment so the connection stays open
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        EventBus.unsubscribe(q)


# ---------------------------------------------------------------------------
# Transaction SSE
# ---------------------------------------------------------------------------

@stream_bp.route("/stream/transactions")
@query_token_required
def stream_transactions():
    """
    SSE endpoint — pushes new transaction events in real time.

    Each event has the shape:
        event: transaction
        data: { "type": "transaction", "data": { ...tx fields... }, "source": "local"|"peer" }
    """
    return Response(
        stream_with_context(_sse_generator("transaction")),
        content_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",     # disable nginx buffering if behind proxy
            "Connection":         "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# General status / peer SSE
# ---------------------------------------------------------------------------

@stream_bp.route("/stream/status")
@query_token_required
def stream_status():
    """
    SSE endpoint — pushes node status and peer connection events.
    """
    return Response(
        stream_with_context(_sse_generator("all")),
        content_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",
            "Connection":         "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Per-client SSE (routed — only events for this client_id)
# ---------------------------------------------------------------------------

def _client_sse_generator(client_id: str):
    """Generator that yields SSE events routed to a specific client_id."""
    q = NotificationService.connect(client_id)
    NotificationService.mark_online_in_db(client_id)
    try:
        yield _format_sse({"type": "connected", "client_id": client_id}, "status")
        while True:
            try:
                event = q.get(timeout=20)
                yield _format_sse(event, event.get("type", "message"))
            except queue.Empty:
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        NotificationService.disconnect(client_id, q)
        NotificationService.mark_offline_in_db(client_id)


@stream_bp.route("/stream/client/<client_id>")
@query_token_required
def stream_client(client_id: str):
    """
    Per-client SSE endpoint — pushes events addressed only to ``client_id``.

    The client app's ``routes/stream.py`` connects here and re-streams
    events to the browser.
    """
    return Response(
        stream_with_context(_client_sse_generator(client_id)),
        content_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )

def _my_sse_generator(account_ids):
    """Generator that yields SSE-formatted events touching only user's accounts."""
    q = EventBus.subscribe()
    try:
        yield _format_sse({"type": "connected", "subscribers": EventBus.subscriber_count()}, "status")
        while True:
            try:
                event = q.get(timeout=20)
                if event.get("type") == "transaction":
                    data = event.get("data", {})
                    # event.data structure is {"classical": {"sender": "...", "receiver": "..."}}
                    classical = data.get("classical", {})
                    if classical.get("sender") in account_ids or classical.get("receiver") in account_ids:
                        yield _format_sse(event, "transaction")
            except queue.Empty:
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
    finally:
        EventBus.unsubscribe(q)

@stream_bp.route("/stream/my_transactions")
@query_token_required
def stream_my_transactions():
    """SSE endpoint tracking only transactions relevant to the authenticated user."""
    # jwt_claims were decoded and cached in g by query_token_required
    user_id = int(g.jwt_claims.get("sub"))

    user = db.session.get(User, user_id)
    if not user:
        from flask import jsonify
        return jsonify({"error": "User not found"}), 401
    accounts = db.session.query(Account).filter_by(user_id=user.id).all()
    account_ids = [a.account_number for a in accounts]

    return Response(
        stream_with_context(_my_sse_generator(account_ids)),
        content_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",
            "Connection":         "keep-alive",
        },
    )

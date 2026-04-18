"""
NotificationService — per-client SSE event routing.

Replaces ``PeerService`` from the P2P era.  Instead of broadcasting a
transaction to all known nodes over HMAC-signed HTTP, this service maintains
an in-memory SSE queue for each connected client and routes events only to
the intended recipient.

Usage (server side, inside transaction_service):
    NotificationService.push_to_client("C2", {"type": "transaction", "data": {...}})

Usage (stream route, one queue per SSE connection):
    q = NotificationService.connect("C1")
    try:
        event = q.get(timeout=20)
        yield format_sse(event)
    finally:
        NotificationService.disconnect("C1", q)
"""
from __future__ import annotations

import queue
import threading
from datetime import datetime, timezone

from app.utils.logger import logger


class NotificationService:
    """Routes SSE events to specific connected clients by client_id."""

    # Map of client_id → list of active queues (one per open SSE connection)
    _lock:    threading.Lock                         = threading.Lock()
    _clients: dict[str, list[queue.Queue]]           = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def connect(cls, client_id: str, maxsize: int = 100) -> queue.Queue:
        """
        Register a new SSE connection for ``client_id``.
        Returns the queue the stream route should read from.
        """
        q = queue.Queue(maxsize=maxsize)
        with cls._lock:
            cls._clients.setdefault(client_id, []).append(q)
        logger.debug("SSE client connected: %s (queues: %d)", client_id, len(cls._clients[client_id]))
        return q

    @classmethod
    def disconnect(cls, client_id: str, q: queue.Queue) -> None:
        """Remove a single SSE connection queue for ``client_id``."""
        with cls._lock:
            queues = cls._clients.get(client_id, [])
            try:
                queues.remove(q)
            except ValueError:
                pass
            if not queues:
                cls._clients.pop(client_id, None)
        logger.debug("SSE client disconnected: %s", client_id)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    @classmethod
    def push_to_client(cls, client_id: str, event: dict) -> bool:
        """
        Push an event to all active SSE queues for ``client_id``.

        Returns True if at least one queue received the event,
        False if the client is not currently connected.
        """
        with cls._lock:
            queues = list(cls._clients.get(client_id, []))

        if not queues:
            logger.debug("push_to_client: no SSE connection for %s — event dropped", client_id)
            return False

        delivered = False
        dead: list[queue.Queue] = []
        for q in queues:
            try:
                q.put_nowait(event)
                delivered = True
            except queue.Full:
                dead.append(q)

        # Prune stale queues
        if dead:
            with cls._lock:
                for q in dead:
                    try:
                        cls._clients.get(client_id, []).remove(q)
                    except ValueError:
                        pass

        logger.debug("push_to_client: %s — delivered=%s", client_id, delivered)
        return delivered

    @classmethod
    def broadcast_to_all(cls, event: dict) -> None:
        """Push ``event`` to every connected client (used for system alerts)."""
        with cls._lock:
            all_client_ids = list(cls._clients.keys())
        for cid in all_client_ids:
            cls.push_to_client(cid, event)

    # ------------------------------------------------------------------
    # Presence helpers
    # ------------------------------------------------------------------

    @classmethod
    def online_client_ids(cls) -> list[str]:
        """Return the list of client_ids with at least one active SSE connection."""
        with cls._lock:
            return [cid for cid, qs in cls._clients.items() if qs]

    @classmethod
    def is_online(cls, client_id: str) -> bool:
        with cls._lock:
            return bool(cls._clients.get(client_id))

    @classmethod
    def mark_online_in_db(cls, client_id: str) -> None:
        """Update the Client row's status and last_seen (call inside app context)."""
        try:
            from app import db
            from app.models.client import Client
            client = db.session.query(Client).filter_by(client_id=client_id).first()
            if client:
                client.touch()
                db.session.commit()
        except Exception as exc:
            logger.warning("mark_online_in_db failed for %s: %s", client_id, exc)

    @classmethod
    def mark_offline_in_db(cls, client_id: str) -> None:
        """Set Client row status to 'offline' (call inside app context)."""
        try:
            from app import db
            from app.models.client import Client
            client = db.session.query(Client).filter_by(client_id=client_id).first()
            if client:
                client.status = "offline"
                db.session.commit()
        except Exception as exc:
            logger.warning("mark_offline_in_db failed for %s: %s", client_id, exc)

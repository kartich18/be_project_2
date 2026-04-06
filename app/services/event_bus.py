"""
EventBus — thread-safe in-memory pub/sub for real-time SSE streaming.

Usage:
    # Publishing (from transaction_service after commit):
    EventBus.publish({"type": "transaction", "data": tx.to_dict()})

    # Subscribing (from an SSE route, one queue per client connection):
    q = EventBus.subscribe()
    try:
        while True:
            event = q.get(timeout=20)   # blocks until event or timeout
            yield format_sse(event)
    finally:
        EventBus.unsubscribe(q)
"""
import queue
import threading
from typing import Iterator


class EventBus:
    """Thread-safe broadcast event bus using in-memory queues."""

    _lock:        threading.Lock          = threading.Lock()
    _subscribers: list[queue.Queue]       = []

    @classmethod
    def publish(cls, event: dict) -> None:
        """Broadcast an event to all active SSE subscribers."""
        with cls._lock:
            dead = []
            for q in cls._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(q)
            # Drop queues that are too full (stale clients)
            for q in dead:
                cls._subscribers.remove(q)

    @classmethod
    def subscribe(cls, maxsize: int = 100) -> queue.Queue:
        """Register a new subscriber. Returns a queue for this client."""
        q = queue.Queue(maxsize=maxsize)
        with cls._lock:
            cls._subscribers.append(q)
        return q

    @classmethod
    def unsubscribe(cls, q: queue.Queue) -> None:
        """Remove a subscriber queue."""
        with cls._lock:
            try:
                cls._subscribers.remove(q)
            except ValueError:
                pass

    @classmethod
    def subscriber_count(cls) -> int:
        """Return number of active SSE subscribers."""
        with cls._lock:
            return len(cls._subscribers)

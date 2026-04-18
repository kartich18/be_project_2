"""
client_app/services/sync_service.py — local SQLite persistence for the client.

When the SSE relay receives a transaction pushed by the server, this service
writes it to the client's own SQLite database so the dashboard can show it
even after a page refresh.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from client_app import client_db
from client_app.models.local_transaction import LocalTransaction


class SyncService:
    """Save and retrieve transactions from the per-client local SQLite."""

    @staticmethod
    def save_transaction(data: dict, direction: str = "received") -> Optional[LocalTransaction]:
        """
        Persist a transaction record to the local DB.

        Args:
            data:       dict returned by the server's transaction response.
                        Can be the top-level response or the nested ``classical``
                        sub-dict — we extract what we need.
            direction:  ``"sent"`` or ``"received"``

        Returns:
            The saved LocalTransaction instance, or None on error.
        """
        try:
            # The server response has a "classical" key at the top level.
            # When called from the stream relay, data may already be the full
            # response dict; when called from transaction route it's the same.
            # We use the classical record for the canonical business fields.
            classical = data.get("classical") if isinstance(data.get("classical"), dict) else data

            tx = LocalTransaction(
                server_tx_id  = classical.get("id"),
                sender        = classical.get("sender", ""),
                receiver      = classical.get("receiver", ""),
                amount        = float(classical.get("amount", 0)),
                currency      = classical.get("currency", "INR"),
                status        = classical.get("status", "success"),
                crypto_method = classical.get("crypto_method", ""),
                total_time_ms = float(classical.get("total_time_ms", 0)),
                direction     = direction,
                received_at   = datetime.now(timezone.utc),
            )
            client_db.session.add(tx)
            client_db.session.commit()
            return tx
        except Exception as exc:
            client_db.session.rollback()
            from flask import current_app
            current_app.logger.warning("SyncService.save_transaction failed: %s", exc)
            return None

    @staticmethod
    def get_local_transactions(limit: int = 100) -> list[dict]:
        """Return recent local transactions as a list of dicts."""
        rows = (
            client_db.session.query(LocalTransaction)
            .order_by(LocalTransaction.received_at.desc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in rows]

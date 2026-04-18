"""
client_app/models/local_transaction.py — lightweight local transaction store.

This is NOT a copy of the server's full Transaction model.  It stores only the
business-relevant fields needed to render the client dashboard and provide a
local audit trail — no heavy crypto-timing columns, no key metadata.
"""
from __future__ import annotations

from datetime import datetime, timezone

from client_app import client_db


class LocalTransaction(client_db.Model):
    """A locally-cached transaction record (sent or received)."""

    __tablename__ = "local_transactions"

    id            = client_db.Column(client_db.Integer, primary_key=True, autoincrement=True)
    server_tx_id  = client_db.Column(client_db.Integer, nullable=True)   # ID from the server DB
    sender        = client_db.Column(client_db.String(128), nullable=False)
    receiver      = client_db.Column(client_db.String(128), nullable=False)
    amount        = client_db.Column(client_db.Float,        nullable=False)
    currency      = client_db.Column(client_db.String(8),    nullable=False, default="INR")
    status        = client_db.Column(client_db.String(16),   nullable=False, default="success")
    crypto_method = client_db.Column(client_db.String(24),   nullable=True)
    total_time_ms = client_db.Column(client_db.Float,        nullable=True)
    direction     = client_db.Column(client_db.String(8),    nullable=False, default="received")  # "sent" | "received"
    received_at   = client_db.Column(client_db.DateTime,     nullable=False,
                                     default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "server_tx_id":  self.server_tx_id,
            "sender":        self.sender,
            "receiver":      self.receiver,
            "amount":        self.amount,
            "currency":      self.currency,
            "status":        self.status,
            "crypto_method": self.crypto_method,
            "total_time_ms": self.total_time_ms,
            "direction":     self.direction,
            "received_at":   self.received_at.isoformat() if self.received_at else None,
        }

    def __repr__(self) -> str:
        return f"<LocalTransaction id={self.id} {self.sender}→{self.receiver} {self.direction}>"

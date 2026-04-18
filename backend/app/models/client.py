"""
Client model — tracks registered client nodes in the client-server network.

Each row represents one client Flask app that has registered with the central
server.  Replaces the old ``Peer`` model (P2P era).
"""
from datetime import datetime, timezone

from app import db


class Client(db.Model):
    """A registered client node."""

    __tablename__ = "clients"

    id            = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    client_id     = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    username      = db.Column(db.String(64),  nullable=True)   # bound user account (optional)
    port          = db.Column(db.Integer,     nullable=False, default=5001)
    ip_address    = db.Column(db.String(45),  nullable=True)
    registered_at = db.Column(db.DateTime,    nullable=False,
                               default=lambda: datetime.now(timezone.utc))
    last_seen     = db.Column(db.DateTime,    nullable=True)
    status        = db.Column(db.String(16),  nullable=False, default="offline")  # "online" | "offline"

    # ------------------------------------------------------------------

    def touch(self) -> None:
        """Mark this client as recently seen and online."""
        self.last_seen = datetime.now(timezone.utc)
        self.status = "online"

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "client_id":     self.client_id,
            "username":      self.username,
            "port":          self.port,
            "ip_address":    self.ip_address,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen":     self.last_seen.isoformat() if self.last_seen else None,
            "status":        self.status,
        }

    def __repr__(self) -> str:
        return f"<Client {self.client_id} status={self.status}>"

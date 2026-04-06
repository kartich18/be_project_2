"""
Peer model — tracks known peer nodes in the P2P network.

Each row represents one remote Flask node that has registered with this node.
"""
from datetime import datetime, timezone

from app import db


class Peer(db.Model):
    """A registered peer node in the P2P network."""

    __tablename__ = "peers"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hostname    = db.Column(db.String(255), nullable=True)
    ip_address  = db.Column(db.String(45),  nullable=False)
    port        = db.Column(db.Integer,      nullable=False, default=5000)
    registered_at = db.Column(db.DateTime,  nullable=False,
                               default=lambda: datetime.now(timezone.utc))
    last_seen   = db.Column(db.DateTime,    nullable=True)
    status      = db.Column(db.String(16),  nullable=False, default="active")  # "active" | "unreachable"

    __table_args__ = (
        db.UniqueConstraint("ip_address", "port", name="uq_peer_ip_port"),
    )

    @property
    def base_url(self) -> str:
        """Return the HTTPS base URL for this peer."""
        scheme = "https"
        return f"{scheme}://{self.ip_address}:{self.port}"

    def touch(self) -> None:
        """Mark this peer as recently seen."""
        self.last_seen = datetime.now(timezone.utc)
        self.status = "active"

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "hostname":      self.hostname,
            "ip_address":    self.ip_address,
            "port":          self.port,
            "base_url":      self.base_url,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen":     self.last_seen.isoformat() if self.last_seen else None,
            "status":        self.status,
        }

    def __repr__(self) -> str:
        return f"<Peer {self.ip_address}:{self.port} status={self.status}>"

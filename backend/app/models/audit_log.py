"""
AuditLog model — append-only ledger for cryptographic & transaction events.
"""
from datetime import datetime, timezone
import json

from app import db

class AuditLog(db.Model):
    """Immutable audit record for system events."""

    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=True)
    
    event_type = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False)  # "success", "failed", "pending"
    details = db.Column(db.Text, nullable=True)  # JSON blob

    # Relationships
    user = db.relationship("User", lazy="select")
    transaction = db.relationship("Transaction", lazy="select")

    def set_details(self, data: dict):
        self.details = json.dumps(data)

    def get_details(self) -> dict:
        if self.details:
            return json.loads(self.details)
        return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "transaction_id": self.transaction_id,
            "event_type": self.event_type,
            "status": self.status,
            "details": self.get_details(),
        }

    def __repr__(self) -> str:
        return f"<AuditLog {self.event_type} status={self.status}>"

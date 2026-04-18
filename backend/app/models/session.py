"""
Session model — tracks device sessions for a user, enabling token revocation.
"""
from datetime import datetime, timezone

from app import db


class Session(db.Model):
    """Stores user session details for refresh token validation."""

    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    device_id = db.Column(db.String(255), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("sessions", lazy=True, cascade="all, delete-orphan"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked": self.revoked,
        }

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id} revoked={self.revoked}>"

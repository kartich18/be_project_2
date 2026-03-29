"""Key rotation audit trail model."""

from datetime import datetime, timezone
import uuid

from app import db


class KeyRotationAudit(db.Model):
    """Audit row for a key rotation event."""

    __tablename__ = "key_rotation_audit"

    rotation_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    old_key_id = db.Column(db.String(36), nullable=True)
    new_key_id = db.Column(db.String(36), nullable=True)
    rotated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    rotation_reason = db.Column(db.String(50), nullable=False, default="auto")

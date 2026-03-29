"""Key metadata model for rotation health analytics."""

from datetime import datetime, timedelta, timezone
import uuid

from app import db


class KeyMetadata(db.Model):
    """Represents cryptographic key lifecycle metadata."""

    __tablename__ = "key_metadata"

    key_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    algorithm = db.Column(db.String(20), nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_used_at = db.Column(db.DateTime, nullable=True)
    rotation_due_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=90),
    )
    status = db.Column(db.String(20), nullable=False, default="active")
    key_version = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        db.Index("idx_key_algorithm_status", "algorithm", "status"),
        db.Index("idx_rotation_due_at", "rotation_due_at"),
        db.Index("idx_key_created_at", "created_at"),
    )

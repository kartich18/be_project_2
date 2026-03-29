"""Security event model for failure/rejection analytics."""

from datetime import datetime, timezone
import uuid

from app import db


class SecurityEvent(db.Model):
    """Security-relevant event captured for analytics and audit."""

    __tablename__ = "security_events"

    event_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    event_type = db.Column(db.String(50), nullable=False)
    algorithm = db.Column(db.String(20), nullable=True)
    sender = db.Column(db.String(128), nullable=True)
    receiver = db.Column(db.String(128), nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    latency_ms = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.Index("idx_security_timestamp", "timestamp"),
        db.Index("idx_security_algorithm_timestamp", "algorithm", "timestamp"),
        db.Index("idx_security_event_type", "event_type"),
    )

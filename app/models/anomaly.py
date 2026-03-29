"""Anomaly model for detected security/performance anomalies."""

from datetime import datetime, timezone
import uuid

from app import db


class Anomaly(db.Model):
    """Detected anomaly entity with severity metadata."""

    __tablename__ = "anomalies"

    anomaly_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detected_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    anomaly_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    metric_name = db.Column(db.String(100), nullable=True)
    baseline_value = db.Column(db.Float, nullable=True)
    current_value = db.Column(db.Float, nullable=True)
    delta_pct = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    acknowledged = db.Column(db.Boolean, nullable=False, default=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.Index("idx_anomaly_detected_at", "detected_at"),
        db.Index("idx_anomaly_severity", "severity"),
        db.Index("idx_anomaly_resolved", "resolved"),
    )

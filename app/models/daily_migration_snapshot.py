"""Daily migration snapshot model for trend analytics."""

from datetime import datetime, timezone

from app import db


class DailyMigrationSnapshot(db.Model):
    """Stores daily algorithm adoption snapshots."""

    __tablename__ = "daily_migration_snapshot"

    snapshot_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    snapshot_date = db.Column(db.Date, nullable=False, unique=True)
    rsa_count = db.Column(db.Integer, nullable=False, default=0)
    mlkem_count = db.Column(db.Integer, nullable=False, default=0)
    hybrid_count = db.Column(db.Integer, nullable=False, default=0)
    total_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("idx_snapshot_date", "snapshot_date"),
    )

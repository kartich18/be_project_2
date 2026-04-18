"""
User model — stores authenticated users for the banking dashboard.

Passwords are hashed with bcrypt. No plaintext is ever stored.
"""
from datetime import datetime, timezone

import bcrypt

from app import db


class User(db.Model):
    """Authenticated user account."""

    __tablename__ = "users"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username     = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email        = db.Column(db.String(128), unique=True, nullable=True)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    role         = db.Column(db.String(16), nullable=False, default="viewer")  # "admin" | "viewer"
    created_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    last_login   = db.Column(db.DateTime, nullable=True)

    # ------------------------------------------------------------------

    def set_password(self, plaintext: str) -> None:
        """Hash and store the password using bcrypt."""
        self.password_hash = bcrypt.hashpw(
            plaintext.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        )

    def check_password(self, plaintext: str) -> bool:
        """Return True if plaintext matches the stored hash."""
        return bcrypt.checkpw(plaintext.encode("utf-8"), self.password_hash)

    def to_dict(self) -> dict:
        """Return a safe, JSON-serialisable dict (no password hash)."""
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "role":       self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role}>"

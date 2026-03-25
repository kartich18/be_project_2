"""
Transaction model — stores transaction data with cryptographic benchmarks.

Each row records one crypto-method run (RSA-2048 *or* ML-KEM-768) for a
single banking transaction, including all timing metrics produced by the
crypto layer.
"""

from datetime import datetime, timezone

from app import db


class Transaction(db.Model):
    """Encrypted-transaction audit record."""

    __tablename__ = "transactions"

    # --- identifiers --------------------------------------------------------
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # --- business fields ----------------------------------------------------
    amount = db.Column(db.Float, nullable=False)
    sender = db.Column(db.String(128), nullable=False)
    receiver = db.Column(db.String(128), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="INR")

    # --- crypto metadata ----------------------------------------------------
    crypto_method = db.Column(
        db.String(16), nullable=False
    )  # "RSA-2048" or "ML-KEM-768"

    # timing (milliseconds)
    key_gen_time_ms = db.Column(db.Float, nullable=False)
    encrypt_time_ms = db.Column(db.Float, nullable=False)
    decrypt_time_ms = db.Column(db.Float, nullable=False)
    total_time_ms = db.Column(db.Float, nullable=False)

    # sizes (bytes)
    key_size_bytes = db.Column(db.Integer, nullable=False)
    ciphertext_size_bytes = db.Column(db.Integer, nullable=False)

    # status
    status = db.Column(db.String(16), nullable=False, default="success")

    # -----------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of this row."""
        return {
            "id": self.id,
            "timestamp": (
                self.timestamp.isoformat() if self.timestamp else None
            ),
            "amount": self.amount,
            "sender": self.sender,
            "receiver": self.receiver,
            "currency": self.currency,
            "crypto_method": self.crypto_method,
            "key_gen_time_ms": self.key_gen_time_ms,
            "encrypt_time_ms": self.encrypt_time_ms,
            "decrypt_time_ms": self.decrypt_time_ms,
            "total_time_ms": self.total_time_ms,
            "key_size_bytes": self.key_size_bytes,
            "ciphertext_size_bytes": self.ciphertext_size_bytes,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} method={self.crypto_method} "
            f"total={self.total_time_ms:.2f}ms status={self.status}>"
        )

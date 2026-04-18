"""
Transaction model — stores transaction data with cryptographic benchmarks.

Each row records one crypto-method run (RSA-2048, ML-KEM-512, ML-KEM-768,
or ML-KEM-1024) for a single banking transaction, including all timing
metrics produced by the crypto layer.
"""

from datetime import datetime, timezone
import enum

from app import db


class TransactionState(str, enum.Enum):
    INITIATED = "INITIATED"
    VALIDATED = "VALIDATED"
    CRYPTO_PROCESSED = "CRYPTO_PROCESSED"
    COMMITTED = "COMMITTED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


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
        db.String(24), nullable=False
    )  # "RSA-2048", "ML-KEM-512", "ML-KEM-768", or "ML-KEM-1024"

    # timing (milliseconds)
    key_gen_time_ms = db.Column(db.Float, nullable=False)
    encapsulate_time_ms = db.Column(db.Float, nullable=True)  # PQC-only (KEM encapsulate)
    encrypt_time_ms = db.Column(db.Float, nullable=False)
    decapsulate_time_ms = db.Column(db.Float, nullable=True)  # PQC-only (KEM decapsulate)
    decrypt_time_ms = db.Column(db.Float, nullable=False)
    total_time_ms = db.Column(db.Float, nullable=False)

    # sizes (bytes)
    key_size_bytes = db.Column(db.Integer, nullable=False)    # public key
    secret_key_bytes = db.Column(db.Integer, nullable=True)   # private/secret key (PQC)
    ciphertext_size_bytes = db.Column(db.Integer, nullable=False)

    # stored actual ciphertext (for harvest simulation)
    kem_ciphertext = db.Column(db.LargeBinary, nullable=True)
    aes_ciphertext = db.Column(db.LargeBinary, nullable=True)

    # extended analytics metadata (non-breaking, optional)
    latency_bucket = db.Column(db.String(32), nullable=True)
    failure_reason = db.Column(db.String(255), nullable=True)
    origin_ip      = db.Column(db.String(45), nullable=True)  # LAN IP of originating peer

    # status
    status = db.Column(db.String(32), nullable=False, default=TransactionState.FAILED.value)

    # -----------------------------------------------------------------------

    def advance_state(self, new_state: TransactionState):
        """Transition to a new state."""
        self.status = new_state.value

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
            "encapsulate_time_ms": self.encapsulate_time_ms,
            "encrypt_time_ms": self.encrypt_time_ms,
            "decapsulate_time_ms": self.decapsulate_time_ms,
            "decrypt_time_ms": self.decrypt_time_ms,
            "total_time_ms": self.total_time_ms,
            "key_size_bytes": self.key_size_bytes,
            "secret_key_bytes": self.secret_key_bytes,
            "ciphertext_size_bytes": self.ciphertext_size_bytes,
            "latency_bucket": self.latency_bucket,
            "failure_reason": self.failure_reason,
            "origin_ip":      self.origin_ip,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} method={self.crypto_method} "
            f"total={self.total_time_ms:.2f}ms status={self.status}>"
        )

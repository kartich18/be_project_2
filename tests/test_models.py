"""
Tests for the Transaction SQLAlchemy model (CRUD + to_dict).
"""

import pytest
from datetime import datetime, timezone

from app import create_app, db
from app.models.transaction import Transaction
from config import TestingConfig


@pytest.fixture()
def app():
    """Create a Flask application configured for testing (in-memory DB)."""
    application = create_app(config_class=TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def session(app):
    """Provide a transactional DB session."""
    with app.app_context():
        yield db.session


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _make_tx(**overrides) -> Transaction:
    """Return a Transaction with sensible defaults; override any field."""
    defaults = dict(
        amount=1000.0,
        sender="Alice",
        receiver="Bob",
        currency="INR",
        crypto_method="RSA-2048",
        key_gen_time_ms=45.0,
        encrypt_time_ms=1.5,
        decrypt_time_ms=2.0,
        total_time_ms=48.5,
        key_size_bytes=294,
        ciphertext_size_bytes=256,
        status="success",
    )
    defaults.update(overrides)
    return Transaction(**defaults)


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

class TestTransactionModel:
    """Transaction ORM model tests."""

    def test_create_and_read(self, session):
        """Insert a row and read it back."""
        tx = _make_tx()
        session.add(tx)
        session.commit()

        fetched = session.get(Transaction, tx.id)
        assert fetched is not None
        assert fetched.amount == 1000.0
        assert fetched.sender == "Alice"
        assert fetched.crypto_method == "RSA-2048"

    def test_defaults(self, session):
        """Timestamp and status should get default values."""
        tx = _make_tx()
        session.add(tx)
        session.commit()

        assert tx.timestamp is not None
        assert isinstance(tx.timestamp, datetime)
        assert tx.status == "success"

    def test_currency_default(self, session):
        """Currency defaults to INR when not supplied."""
        tx = Transaction(
            amount=500,
            sender="X",
            receiver="Y",
            crypto_method="RSA-2048",
            key_gen_time_ms=1,
            encrypt_time_ms=1,
            decrypt_time_ms=1,
            total_time_ms=3,
            key_size_bytes=294,
            ciphertext_size_bytes=256,
        )
        session.add(tx)
        session.commit()
        assert tx.currency == "INR"

    def test_to_dict(self, session):
        """to_dict() returns all expected keys with correct values."""
        tx = _make_tx(amount=2500.50, sender="Carol", receiver="Dave")
        session.add(tx)
        session.commit()

        d = tx.to_dict()
        assert d["id"] == tx.id
        assert d["amount"] == 2500.50
        assert d["sender"] == "Carol"
        assert d["receiver"] == "Dave"
        assert d["crypto_method"] == "RSA-2048"
        assert d["key_gen_time_ms"] == 45.0
        assert d["encrypt_time_ms"] == 1.5
        assert d["decrypt_time_ms"] == 2.0
        assert d["total_time_ms"] == 48.5
        assert d["key_size_bytes"] == 294
        assert d["ciphertext_size_bytes"] == 256
        assert d["status"] == "success"
        # timestamp should be an ISO string
        assert "T" in d["timestamp"]

    def test_to_dict_keys_complete(self, session):
        """to_dict() must contain every column key."""
        tx = _make_tx()
        session.add(tx)
        session.commit()

        expected_keys = {
            "id", "timestamp", "amount", "sender", "receiver", "currency",
            "crypto_method", "key_gen_time_ms", "encrypt_time_ms",
            "decrypt_time_ms", "total_time_ms", "key_size_bytes",
            "ciphertext_size_bytes", "status",
        }
        assert set(tx.to_dict().keys()) == expected_keys

    def test_query_by_method(self, session):
        """Filter transactions by crypto_method."""
        session.add(_make_tx(crypto_method="RSA-2048"))
        session.add(_make_tx(crypto_method="ML-KEM-768"))
        session.add(_make_tx(crypto_method="RSA-2048"))
        session.commit()

        rsa_rows = (
            session.query(Transaction)
            .filter_by(crypto_method="RSA-2048")
            .all()
        )
        assert len(rsa_rows) == 2

    def test_repr(self, session):
        """__repr__ returns a useful string."""
        tx = _make_tx()
        session.add(tx)
        session.commit()

        r = repr(tx)
        assert "Transaction" in r
        assert "RSA-2048" in r

    def test_multiple_inserts(self, session):
        """Bulk insert should work and IDs should auto-increment."""
        txns = [_make_tx(amount=i * 100) for i in range(5)]
        session.add_all(txns)
        session.commit()

        assert session.query(Transaction).count() == 5
        ids = [t.id for t in txns]
        assert len(set(ids)) == 5  # all unique

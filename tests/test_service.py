"""
Tests for TransactionService — process_transaction() and get_metrics().
"""

import pytest

from app import create_app, db
from app.models.transaction import Transaction
from app.services.transaction_service import TransactionService
from app.crypto.pqc import PQC_AVAILABLE
from config import TestingConfig


@pytest.fixture()
def app():
    """Create a Flask test application with in-memory DB."""
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


SAMPLE_DATA = {
    "amount": 1000.0,
    "sender": "Alice",
    "receiver": "Bob",
    "currency": "INR",
}


# -----------------------------------------------------------------------
# process_transaction
# -----------------------------------------------------------------------

class TestProcessTransaction:
    """Tests for TransactionService.process_transaction()."""

    def test_classical_result_present(self, session):
        """Classical result should always be present."""
        result = TransactionService.process_transaction(SAMPLE_DATA, session)
        assert "classical" in result
        cl = result["classical"]
        assert cl["crypto_method"] == "RSA-2048"
        assert cl["status"] == "success"
        assert cl["amount"] == 1000.0

    def test_classical_timing_fields(self, session):
        """All timing fields should be positive floats."""
        result = TransactionService.process_transaction(SAMPLE_DATA, session)
        cl = result["classical"]
        for key in ("key_gen_time_ms", "encrypt_time_ms", "decrypt_time_ms", "total_time_ms"):
            assert isinstance(cl[key], float)
            assert cl[key] > 0

    def test_classical_row_persisted(self, session):
        """A Transaction row should be written to the DB."""
        TransactionService.process_transaction(SAMPLE_DATA, session)
        rows = session.query(Transaction).filter_by(crypto_method="RSA-2048").all()
        assert len(rows) >= 1

    def test_pqc_skipped_when_unavailable(self, session):
        """When liboqs is missing, result should contain pqc_error."""
        if PQC_AVAILABLE:
            pytest.skip("liboqs is installed — cannot test fallback path")
        result = TransactionService.process_transaction(SAMPLE_DATA, session)
        assert "pqc_error" in result
        assert "liboqs" in result["pqc_error"].lower() or "skipped" in result["pqc_error"].lower()

    @pytest.mark.skipif(not PQC_AVAILABLE, reason="liboqs not installed")
    def test_pqc_result_present(self, session):
        """When liboqs is available, PQC result should be present."""
        result = TransactionService.process_transaction(SAMPLE_DATA, session)
        assert "pqc" in result
        pqc = result["pqc"]
        assert pqc["crypto_method"] == "ML-KEM-768"
        assert pqc["status"] == "success"

    @pytest.mark.skipif(not PQC_AVAILABLE, reason="liboqs not installed")
    def test_pqc_row_persisted(self, session):
        """PQC Transaction row should be persisted when liboqs is available."""
        TransactionService.process_transaction(SAMPLE_DATA, session)
        rows = session.query(Transaction).filter_by(crypto_method="ML-KEM-768").all()
        assert len(rows) >= 1

    def test_default_currency(self, session):
        """Currency should default to INR when omitted."""
        data = {"amount": 500, "sender": "X", "receiver": "Y"}
        result = TransactionService.process_transaction(data, session)
        assert result["classical"]["currency"] == "INR"


# -----------------------------------------------------------------------
# get_metrics
# -----------------------------------------------------------------------

def _seed_transactions(session, n_classical=3, n_pqc=2):
    """Insert sample Transaction rows for metrics tests."""
    for i in range(n_classical):
        session.add(Transaction(
            amount=100 * (i + 1),
            sender="A",
            receiver="B",
            crypto_method="RSA-2048",
            key_gen_time_ms=40.0 + i,
            encrypt_time_ms=1.0 + i * 0.5,
            decrypt_time_ms=2.0 + i * 0.5,
            total_time_ms=43.0 + i * 2,
            key_size_bytes=294,
            ciphertext_size_bytes=256,
        ))
    for i in range(n_pqc):
        session.add(Transaction(
            amount=200 * (i + 1),
            sender="C",
            receiver="D",
            crypto_method="ML-KEM-768",
            key_gen_time_ms=0.5 + i * 0.1,
            encrypt_time_ms=0.2 + i * 0.05,
            decrypt_time_ms=0.1 + i * 0.05,
            total_time_ms=0.8 + i * 0.2,
            key_size_bytes=1184,
            ciphertext_size_bytes=1088,
        ))
    session.commit()


class TestGetMetrics:
    """Tests for TransactionService.get_metrics()."""

    def test_both_methods(self, session):
        """Should return sections for both classical and pqc."""
        _seed_transactions(session)
        metrics = TransactionService.get_metrics(session)
        assert "classical" in metrics
        assert "pqc" in metrics

    def test_classical_count(self, session):
        """Classical count should match seeded rows."""
        _seed_transactions(session, n_classical=5, n_pqc=0)
        metrics = TransactionService.get_metrics(session)
        assert metrics["classical"]["count"] == 5

    def test_pqc_count(self, session):
        """PQC count should match seeded rows."""
        _seed_transactions(session, n_classical=0, n_pqc=4)
        metrics = TransactionService.get_metrics(session)
        assert metrics["pqc"]["count"] == 4

    def test_averages_reasonable(self, session):
        """Avg values should be between min and max of seeded data."""
        _seed_transactions(session, n_classical=3)
        metrics = TransactionService.get_metrics(session)
        avg = metrics["classical"]["avg_key_gen_ms"]
        assert 40.0 <= avg <= 42.0

    def test_empty_db(self, session):
        """Empty DB should return zero counts."""
        metrics = TransactionService.get_metrics(session)
        assert metrics["classical"]["count"] == 0
        assert metrics["pqc"]["count"] == 0

    def test_filter_by_method(self, session):
        """Filtering by method should return only that method."""
        _seed_transactions(session, n_classical=3, n_pqc=2)
        metrics = TransactionService.get_metrics(session, method="RSA-2048")
        assert "classical" in metrics
        assert "pqc" not in metrics

    def test_limit(self, session):
        """Limit param should cap the number of rows considered."""
        _seed_transactions(session, n_classical=10, n_pqc=0)
        metrics = TransactionService.get_metrics(session, limit=5)
        assert metrics["classical"]["count"] == 5

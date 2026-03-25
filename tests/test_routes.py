"""
Tests for REST API routes — POST /api/transaction, GET /api/metrics,
GET /api/benchmark.

Uses Flask test client with TestingConfig (in-memory SQLite).
"""

import pytest

from app import create_app, db
from app.models.transaction import Transaction
from config import TestingConfig


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

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
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


VALID_PAYLOAD = {
    "amount": 1000.0,
    "sender": "Alice",
    "receiver": "Bob",
}


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


# -----------------------------------------------------------------------
# POST /api/transaction
# -----------------------------------------------------------------------

class TestPostTransaction:
    """Tests for POST /api/transaction."""

    def test_valid_transaction_returns_201(self, client):
        """Valid payload should return 201 with classical result."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["crypto_method"] == "RSA-2048"
        assert data["classical"]["status"] == "success"

    def test_response_contains_timing_fields(self, client):
        """Response should include timing metrics."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD)
        data = resp.get_json()
        cl = data["classical"]
        for field in ("key_gen_time_ms", "encrypt_time_ms",
                      "decrypt_time_ms", "total_time_ms"):
            assert field in cl
            assert cl[field] > 0

    def test_missing_amount_returns_400(self, client):
        """Missing 'amount' field should return 400."""
        resp = client.post("/api/transaction", json={
            "sender": "Alice", "receiver": "Bob",
        })
        assert resp.status_code == 400
        assert "amount" in resp.get_json()["error"].lower()

    def test_missing_sender_returns_400(self, client):
        """Missing 'sender' field should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": 100, "receiver": "Bob",
        })
        assert resp.status_code == 400
        assert "sender" in resp.get_json()["error"].lower()

    def test_empty_body_returns_400(self, client):
        """Empty / non-JSON body should return 400."""
        resp = client.post("/api/transaction",
                           data="", content_type="application/json")
        assert resp.status_code == 400

    def test_negative_amount_returns_400(self, client):
        """Negative amount should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": -50, "sender": "Alice", "receiver": "Bob",
        })
        assert resp.status_code == 400

    def test_same_sender_receiver_returns_400(self, client):
        """Sender == receiver should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": 100, "sender": "Alice", "receiver": "Alice",
        })
        assert resp.status_code == 400

    def test_transaction_persisted_to_db(self, app, client):
        """Transaction should appear in the database after POST."""
        client.post("/api/transaction", json=VALID_PAYLOAD)
        with app.app_context():
            rows = db.session.query(Transaction).all()
            assert len(rows) >= 1  # at least the classical row


# -----------------------------------------------------------------------
# GET /api/metrics
# -----------------------------------------------------------------------

class TestGetMetrics:
    """Tests for GET /api/metrics."""

    def test_empty_db_returns_200(self, client):
        """Empty database should still return 200 with zero counts."""
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["count"] == 0

    def test_metrics_after_seeding(self, app, client):
        """Metrics should reflect seeded transactions."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=5, n_pqc=3)
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["classical"]["count"] == 5
        assert data["pqc"]["count"] == 3

    def test_method_filter(self, app, client):
        """?method=RSA-2048 should return only classical results."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=3, n_pqc=2)
        resp = client.get("/api/metrics?method=RSA-2048")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert "pqc" not in data

    def test_last_param(self, app, client):
        """?last=2 should cap the number of rows considered."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=10, n_pqc=0)
        resp = client.get("/api/metrics?last=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["classical"]["count"] == 2


# -----------------------------------------------------------------------
# GET /api/benchmark
# -----------------------------------------------------------------------

class TestGetBenchmark:
    """Tests for GET /api/benchmark."""

    def test_default_benchmark_returns_200(self, client):
        """Default benchmark should return 200 with classical result."""
        resp = client.get("/api/benchmark?iterations=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["method"] == "RSA-2048"
        assert data["iterations"] == 2

    def test_iterations_param(self, client):
        """?iterations=5 should run exactly 5 iterations."""
        resp = client.get("/api/benchmark?iterations=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["iterations"] == 5
        assert data["classical"]["iterations"] == 5

    def test_invalid_iterations_returns_400(self, client):
        """Non-numeric iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=abc")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_zero_iterations_returns_400(self, client):
        """Zero iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=0")
        assert resp.status_code == 400

    def test_negative_iterations_returns_400(self, client):
        """Negative iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=-5")
        assert resp.status_code == 400

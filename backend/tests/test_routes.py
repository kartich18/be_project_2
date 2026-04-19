"""
Tests for REST API routes — POST /api/transaction, GET /api/metrics,
GET /api/benchmark.

Uses Flask test client with TestingConfig (in-memory SQLite).

Response shape (current 4-pipeline engine):
  {
    "classical": { ...tx fields... },
    "pqc_512":   { ...tx fields... },   # present when liboqs available
    "pqc_768":   { ...tx fields... },   # present when liboqs available
    "pqc_1024":  { ...tx fields... },   # present when liboqs available
    "pqc_error": "..."                  # present when liboqs NOT available
  }
"""

import pytest

from app import create_app, db
from app.models.transaction import Transaction
from app.crypto.pqc import PQC_AVAILABLE
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
def auth_headers(app):
    """Provide a valid JWT token header."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity="test_user")
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


VALID_PAYLOAD = {
    "amount": 1000.0,
    "account_id_from": "Alice",
    "account_id_to": "Bob",
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
    for algo in ("ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"):
        for i in range(n_pqc):
            session.add(Transaction(
                amount=200 * (i + 1),
                sender="C",
                receiver="D",
                crypto_method=algo,
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

    def test_valid_transaction_always_has_classical(self, client, auth_headers):
        """Valid payload must always return 201 with a classical result."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["crypto_method"] == "RSA-2048"
        assert data["classical"]["status"] == "SETTLED"

    @pytest.mark.skipif(not PQC_AVAILABLE, reason="liboqs not installed")
    def test_valid_transaction_has_all_four_pipelines(self, client, auth_headers):
        """With liboqs installed, all four pipeline keys must be present."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        for key in ("classical", "pqc_512", "pqc_768", "pqc_1024"):
            assert key in data, f"Expected key '{key}' missing from response"
            assert data[key]["status"] == "SETTLED"

    @pytest.mark.skipif(not PQC_AVAILABLE, reason="liboqs not installed")
    def test_pqc_method_labels_are_correct(self, client, auth_headers):
        """Each PQC result block must carry the correct crypto_method label."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        data = resp.get_json()
        assert data["pqc_512"]["crypto_method"] == "ML-KEM-512"
        assert data["pqc_768"]["crypto_method"] == "ML-KEM-768"
        assert data["pqc_1024"]["crypto_method"] == "ML-KEM-1024"

    def test_response_contains_timing_fields(self, client, auth_headers):
        """Classical result must include all timing metrics."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        data = resp.get_json()
        cl = data["classical"]
        for field in ("key_gen_time_ms", "encrypt_time_ms",
                      "decrypt_time_ms", "total_time_ms"):
            assert field in cl
            assert cl[field] > 0

    def test_missing_amount_returns_400(self, client, auth_headers):
        """Missing 'amount' field should return 400."""
        resp = client.post("/api/transaction", json={
            "account_id_from": "Alice", "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "amount" in resp.get_json()["error"].lower()

    def test_missing_sender_returns_400(self, client, auth_headers):
        """Missing 'account_id_from' field should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": 100, "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "account_id_from" in resp.get_json()["error"].lower()

    def test_empty_body_returns_400(self, client, auth_headers):
        """Empty / non-JSON body should return 400."""
        resp = client.post("/api/transaction",
                           data="", content_type="application/json", headers=auth_headers)
        assert resp.status_code == 400

    def test_negative_amount_returns_400(self, client, auth_headers):
        """Negative amount should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": -50, "account_id_from": "Alice", "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_same_sender_receiver_returns_400(self, client, auth_headers):
        """Sender == receiver should return 400."""
        resp = client.post("/api/transaction", json={
            "amount": 100, "account_id_from": "Alice", "account_id_to": "Alice",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_transaction_persisted_to_db(self, app, client, auth_headers):
        """At least the classical transaction row must appear in the database."""
        client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        with app.app_context():
            rows = db.session.query(Transaction).filter_by(crypto_method="RSA-2048").all()
            assert len(rows) >= 1


# -----------------------------------------------------------------------
# GET /api/metrics
# -----------------------------------------------------------------------

class TestGetMetrics:
    """Tests for GET /api/metrics."""

    def test_empty_db_returns_200(self, client, auth_headers):
        """Empty database should still return 200 with zero counts for all methods."""
        resp = client.get("/api/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["count"] == 0

    def test_metrics_after_seeding(self, app, client, auth_headers):
        """Metrics should reflect seeded transactions for all four methods."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=5, n_pqc=3)
        resp = client.get("/api/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["classical"]["count"] == 5
        assert data["pqc_512"]["count"] == 3
        assert data["pqc_768"]["count"] == 3
        assert data["pqc_1024"]["count"] == 3

    def test_method_filter(self, app, client, auth_headers):
        """?method=RSA-2048 should return only classical results."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=3, n_pqc=2)
        resp = client.get("/api/metrics?method=RSA-2048", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert "pqc_512" not in data
        assert "pqc_768" not in data
        assert "pqc_1024" not in data

    def test_last_param(self, app, client, auth_headers):
        """?last=2 should cap the number of rows considered."""
        with app.app_context():
            _seed_transactions(db.session, n_classical=10, n_pqc=0)
        resp = client.get("/api/metrics?last=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["classical"]["count"] == 2


# -----------------------------------------------------------------------
# GET /api/benchmark
# -----------------------------------------------------------------------

class TestGetBenchmark:
    """Tests for GET /api/benchmark."""

    def test_default_benchmark_returns_200(self, client, auth_headers):
        """Default benchmark should return 200 with a classical result."""
        resp = client.get("/api/benchmark?iterations=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert data["classical"]["method"] == "RSA-2048"
        assert data["iterations"] == 2

    def test_iterations_param(self, client, auth_headers):
        """?iterations=5 should run exactly 5 iterations."""
        resp = client.get("/api/benchmark?iterations=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["iterations"] == 5
        assert data["classical"]["iterations"] == 5

    def test_invalid_iterations_returns_400(self, client, auth_headers):
        """Non-numeric iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=abc", headers=auth_headers)
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_zero_iterations_returns_400(self, client, auth_headers):
        """Zero iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=0", headers=auth_headers)
        assert resp.status_code == 400

    def test_negative_iterations_returns_400(self, client, auth_headers):
        """Negative iterations should return 400."""
        resp = client.get("/api/benchmark?iterations=-5", headers=auth_headers)
        assert resp.status_code == 400

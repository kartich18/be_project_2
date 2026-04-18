"""
Integration tests — end-to-end flows across API, service, and data layers.

Validates the full stack: POST /api/transaction → DB persistence → GET /api/metrics
reflects the stored data, concurrent request handling, edge cases, and fallback.
"""

import json

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
    "amount": 1500.0,
    "account_id_from": "Alice",
    "account_id_to": "Bob",
}


# -----------------------------------------------------------------------
# E2E: POST → DB → Metrics
# -----------------------------------------------------------------------

class TestPostToMetricsFlow:
    """Submit transactions via API, then verify DB state and metrics."""

    def test_single_transaction_reflected_in_metrics(self, app, client, auth_headers):
        """POST one transaction → GET /api/metrics should reflect it."""
        # 1. Submit a transaction
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        tx_data = resp.get_json()

        # Classical result should always be present
        assert tx_data["classical"]["status"] == "SETTLED"

        # 2. Check DB row count
        with app.app_context():
            classical_count = (
                db.session.query(Transaction)
                .filter_by(crypto_method="RSA-2048")
                .count()
            )
            assert classical_count >= 1

        # 3. Verify metrics endpoint
        metrics_resp = client.get("/api/metrics", headers=auth_headers)
        assert metrics_resp.status_code == 200
        metrics = metrics_resp.get_json()
        assert metrics["classical"]["count"] >= 1
        assert metrics["classical"]["avg_total_ms"] > 0

    def test_multiple_transactions_aggregation(self, app, client, auth_headers):
        """Submit 3 transactions → metrics should aggregate correctly."""
        for i in range(3):
            resp = client.post("/api/transaction", json={
                "amount": 100 * (i + 1),
                "account_id_from": f"Sender{i}",
                "account_id_to": f"Receiver{i}",
            }, headers=auth_headers)
            assert resp.status_code == 201

        metrics_resp = client.get("/api/metrics", headers=auth_headers)
        metrics = metrics_resp.get_json()
        assert metrics["classical"]["count"] == 3

        # Averages should be positive
        assert metrics["classical"]["avg_key_gen_ms"] > 0
        assert metrics["classical"]["avg_encrypt_ms"] > 0
        assert metrics["classical"]["avg_decrypt_ms"] > 0

    def test_method_filter_after_transactions(self, app, client, auth_headers):
        """After submitting, ?method=RSA-2048 should return only classical."""
        client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)

        resp = client.get("/api/metrics?method=RSA-2048", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classical" in data
        assert "pqc_768" not in data


# -----------------------------------------------------------------------
# E2E: POST + Benchmark coexistence
# -----------------------------------------------------------------------

class TestBenchmarkCoexistence:
    """Verify benchmark endpoint works alongside transactions."""

    def test_transaction_then_benchmark(self, client, auth_headers):
        """POST a transaction, then run a small benchmark — both succeed."""
        # Transaction
        resp1 = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp1.status_code == 201

        # Benchmark (small iteration count for speed)
        resp2 = client.get("/api/benchmark?iterations=2", headers=auth_headers)
        assert resp2.status_code == 200
        bench = resp2.get_json()
        assert bench["iterations"] == 2
        assert "classical" in bench


# -----------------------------------------------------------------------
# Dashboard route
# -----------------------------------------------------------------------

class TestDashboardRoute:
    """Verify the dashboard serves HTML."""

    def test_root_returns_json(self, client):
        """GET / should return 200 with JSON content instead of HTML now."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"status" in resp.data


# -----------------------------------------------------------------------
# Edge cases
# -----------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_large_sender_name(self, client, auth_headers):
        """Transaction with a very long sender name should still succeed."""
        resp = client.post("/api/transaction", json={
            "amount": 500.0,
            "account_id_from": "A" * 120,  # Close to 128-char limit
            "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["classical"]["status"] == "SETTLED"

    def test_very_small_amount(self, client, auth_headers):
        """Tiny but positive amount should be accepted."""
        resp = client.post("/api/transaction", json={
            "amount": 0.01,
            "account_id_from": "Alice",
            "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_very_large_amount(self, client, auth_headers):
        """Large amount should be accepted."""
        resp = client.post("/api/transaction", json={
            "amount": 999_999_999.99,
            "account_id_from": "Alice",
            "account_id_to": "Bob",
        }, headers=auth_headers)
        assert resp.status_code == 201


# -----------------------------------------------------------------------
# Concurrent requests
# -----------------------------------------------------------------------

class TestRapidFireRequests:
    """Verify multiple rapid sequential requests are handled correctly."""

    def test_rapid_fire_transactions(self, app, client, auth_headers):
        """5 rapid-fire POSTs should all succeed and create correct DB state."""
        responses = []
        for i in range(5):
            resp = client.post("/api/transaction", json={
                "amount": 100 * (i + 1),
                "account_id_from": f"RapidSender{i}",
                "account_id_to": f"RapidReceiver{i}",
            }, headers=auth_headers)
            responses.append(resp)

        # All should succeed
        for resp in responses:
            assert resp.status_code == 201

        # DB should have 5 classical rows
        with app.app_context():
            classical_count = (
                db.session.query(Transaction)
                .filter_by(crypto_method="RSA-2048")
                .count()
            )
            assert classical_count == 5


# -----------------------------------------------------------------------
# Liboqs fallback
# -----------------------------------------------------------------------

class TestPQCFallback:
    """Verify graceful fallback when liboqs is unavailable."""

    @pytest.mark.skipif(
        PQC_AVAILABLE,
        reason="liboqs IS installed — cannot test fallback path",
    )
    def test_transaction_succeeds_without_liboqs(self, client, auth_headers):
        """Classical path should succeed; response should contain pqc_error."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()

        assert data["classical"]["status"] == "SETTLED"
        assert "pqc_error" in data

    @pytest.mark.skipif(
        not PQC_AVAILABLE,
        reason="liboqs not installed — cannot test PQC success path",
    )
    def test_both_methods_succeed_with_liboqs(self, client, auth_headers):
        """With liboqs installed, both classical and PQC should succeed."""
        resp = client.post("/api/transaction", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()

        assert data["classical"]["status"] == "SETTLED"
        assert "pqc_768" in data
        assert data["pqc_768"]["status"] == "SETTLED"

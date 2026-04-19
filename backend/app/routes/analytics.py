"""Advanced analytics routes for dashboard enhancement."""

from flask import Blueprint, jsonify, request

from app.services.analytics_service import AnalyticsService
from app.utils.logger import logger


analytics_bp = Blueprint("analytics", __name__)



@analytics_bp.route("/v1/analytics/migration-status", methods=["GET"])
def migration_status():
    """Return ML-KEM migration progress and trend."""
    time_window = request.args.get("time_window", default="24h", type=str)

    try:
        result = AnalyticsService.get_migration_status(time_window=time_window)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Migration status endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/algorithm-comparison", methods=["GET"])
def algorithm_comparison():
    """Return comparative performance ratio between RSA and ML-KEM."""
    time_window = request.args.get("time_window", default="24h", type=str)

    try:
        result = AnalyticsService.get_algorithm_comparison(time_window=time_window)
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Algorithm comparison endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/security-health", methods=["GET"])
def security_health():
    """Return failure/rejection rates and overall security status."""
    time_window = request.args.get("time_window", default="24h", type=str)
    algorithm = request.args.get("algorithm", default=None, type=str)

    try:
        result = AnalyticsService.get_security_health(
            time_window=time_window,
            algorithm=algorithm,
        )
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Security health endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/anomalies", methods=["GET"])
def anomalies():
    """Return unresolved anomalies with severity metadata."""
    try:
        result = AnalyticsService.get_anomalies()
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        logger.exception("Anomalies endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@analytics_bp.route("/v1/analytics/signature-health", methods=["GET"])
def signature_health():
    """
    Return digital signature telemetry comparing classical (RSA-PSS)
    and post-quantum (ML-DSA-44/65/87) pipelines.

    Queries Transaction rows where dsa_algorithm IS NOT NULL, grouped
    by whether the algorithm is RSA-PSS (classical) or ML-DSA (PQC).

    Returns:
        200 — signature health dict with classical, pqc_512, pqc_768,
               pqc_1024 sub-dicts and a human-readable summary verdict.
        500 — internal error.
    """
    try:
        from app.models.transaction import Transaction
        from app import db

        # --- helper: aggregate rows into a stats dict ---
        def _agg(rows):
            if not rows:
                return None
            n = len(rows)
            avg_sign   = round(sum(r.sign_time_ms   for r in rows if r.sign_time_ms)   / n, 4)
            avg_verify = round(sum(r.verify_time_ms for r in rows if r.verify_time_ms) / n, 4)
            sig_size   = rows[0].signature_size_bytes
            dsa_pub    = rows[0].dsa_public_key_bytes
            failed     = sum(1 for r in rows if r.status != "SETTLED")
            verified_pct = round((n - failed) / n * 100, 2)
            return {
                "algorithm":           rows[0].dsa_algorithm,
                "avg_sign_ms":         avg_sign,
                "avg_verify_ms":       avg_verify,
                "dsa_public_key_bytes": dsa_pub,
                "signature_size_bytes": sig_size,
                "verified_pct":        verified_pct,
                "sample_count":        n,
            }

        # Query rows with DSA data
        all_rows = (
            db.session.query(Transaction)
            .filter(Transaction.dsa_algorithm.isnot(None))
            .order_by(Transaction.timestamp.desc())
            .limit(500)
            .all()
        )

        classical_rows = [r for r in all_rows if r.dsa_algorithm == "RSA-PSS"]
        pqc_512_rows   = [r for r in all_rows if r.dsa_algorithm == "ML-DSA-44"]
        pqc_768_rows   = [r for r in all_rows if r.dsa_algorithm == "ML-DSA-65"]
        pqc_1024_rows  = [r for r in all_rows if r.dsa_algorithm == "ML-DSA-87"]

        classical_stats = _agg(classical_rows)
        pqc_512_stats   = _agg(pqc_512_rows)
        pqc_768_stats   = _agg(pqc_768_rows)
        pqc_1024_stats  = _agg(pqc_1024_rows)

        # Build verdict comparing RSA-PSS vs ML-DSA-65 (Level 3 baseline)
        verdict = "No signature data available yet — submit a transaction to populate."
        if classical_stats and pqc_768_stats:
            cs = classical_stats["avg_sign_ms"]
            ps = pqc_768_stats["avg_sign_ms"]
            cv = classical_stats["avg_verify_ms"]
            pv = pqc_768_stats["avg_verify_ms"]
            sign_ratio  = round(cs / ps, 2) if ps else 0
            verify_ratio = round(cv / pv, 2) if pv else 0
            rsa_sig_size = classical_stats["signature_size_bytes"] or 256
            ml_sig_size  = pqc_768_stats["signature_size_bytes"] or 3293
            size_delta   = round((ml_sig_size - rsa_sig_size) / rsa_sig_size * 100, 1)

            sign_label   = f"RSA-PSS signs {sign_ratio}× slower" if sign_ratio > 1 else f"ML-DSA-65 signs {round(1/sign_ratio,2)}× slower"
            verify_label = f"RSA-PSS verifies {verify_ratio}× slower" if verify_ratio > 1 else f"ML-DSA-65 verifies {round(1/verify_ratio,2)}× slower"
            verdict = (
                f"{sign_label} than ML-DSA-65. "
                f"{verify_label}. "
                f"ML-DSA-65 signature is {size_delta:+.1f}% larger ({ml_sig_size} B vs {rsa_sig_size} B RSA-PSS) — "
                f"the quantum-safe size tradeoff."
            )

        result = {
            "classical":  classical_stats,
            "pqc_512":    pqc_512_stats,
            "pqc_768":    pqc_768_stats,
            "pqc_1024":   pqc_1024_stats,
            "summary": {
                "verdict":              verdict,
                "pqc_is_quantum_safe":  True,
                "classical_standard":   "RSA-PSS / SHA-256 (FIPS 186-5)",
                "pqc_standard":         "ML-DSA / FIPS 204 (Dilithium)",
                "security_pairing":     "ML-KEM-512↔ML-DSA-44, ML-KEM-768↔ML-DSA-65, ML-KEM-1024↔ML-DSA-87",
            },
        }
        return jsonify(result), 200

    except Exception as exc:  # noqa: BLE001
        logger.exception("Signature health endpoint failed: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
